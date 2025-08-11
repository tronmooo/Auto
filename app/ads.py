import os
import uuid
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
import google.generativeai as genai
from ..extensions import db


def generate_ad_copy_with_gemini(business):
    """
    Generates ad copy using the Gemini API.
    """
    print("Generating ad copy with Gemini...")
    try:
        genai.api_key = business.gemini_api_key
        model = genai.GenerativeModel('gemini-pro')

        prompt = f"""
        You are an AI assistant for a high-end home service business named "{business.business_name}".
        The business specializes in: {business.specialties}.
        The target service area is: {business.service_area}.

        Your task is to generate 5 distinct, compelling ad headlines (max 30 characters each) and 3 distinct, detailed ad descriptions (max 90 characters each) for a Google Ads campaign.

        Instructions:
        - Headlines should be punchy and highlight key services or benefits (e.g., "Luxury Kitchen Remodels", "Free Consultation", "Expert Pool Installation").
        - Descriptions should be more detailed, mentioning the business name and service area.
        - The tone should be professional, trustworthy, and aimed at high-value clients.

        Generate the headlines and descriptions now.
        """

        response = model.generate_content(prompt)
        # Basic parsing, a real implementation would be more robust
        lines = response.text.strip().split('\n')
        headlines = [l for l in lines if l.startswith('Headline')][:5]
        descriptions = [l for l in lines if l.startswith('Description')][:3]

        # Clean up the parsed text
        headlines = [h.split(': ')[1].strip('"') for h in headlines]
        descriptions = [d.split(': ')[1].strip('"') for d in descriptions]

        return {"headlines": headlines, "descriptions": descriptions}

    except Exception as e:
        print(f"Error generating Gemini ad copy: {e}")
        return None


def manage_ad_campaign(business, budget_micros):
    """
    Creates and manages a Google Ads campaign for a business.
    """
    print(f"Starting ad campaign management for {business.business_name}...")

    try:
        # Initialize the Google Ads client. The `google-ads.yaml` file should be
        # configured with developer token, client ID, client secret, and refresh token.
        # The path to this file can be set in an environment variable GOOGLE_ADS_YAML.
        googleads_client = GoogleAdsClient.load_from_env()
        customer_id = business.google_ads_customer_id

        # --- Generate Ad Copy ---
        ad_copy = generate_ad_copy_with_gemini(business)
        if not ad_copy or len(ad_copy['headlines']) < 3 or len(ad_copy['descriptions']) < 2:
            print("Failed to generate sufficient ad copy. Aborting campaign creation.")
            business.campaign_status = "Failed: Ad Copy Generation"
            db.session.commit()
            return

        # --- Services ---
        campaign_service = googleads_client.get_service("CampaignService")
        ad_group_service = googleads_client.get_service("AdGroupService")
        ad_group_ad_service = googleads_client.get_service("AdGroupAdService")
        ad_group_criterion_service = googleads_client.get_service("AdGroupCriterionService")
        campaign_budget_service = googleads_client.get_service("CampaignBudgetService")

        # --- 1. Create a Campaign Budget ---
        budget_operation = googleads_client.get_type("CampaignBudgetOperation")
        campaign_budget = budget_operation.create
        campaign_budget.name = f"Budget for {business.business_name} {uuid.uuid4()}"
        campaign_budget.delivery_method = googleads_client.enums.BudgetDeliveryMethodEnum.STANDARD
        campaign_budget.amount_micros = budget_micros
        budget_response = campaign_budget_service.mutate_campaign_budgets(
            customer_id=customer_id, operations=[budget_operation]
        )
        budget_resource_name = budget_response.results[0].resource_name
        print(f"Created campaign budget: {budget_resource_name}")

        # --- 2. Create a Campaign ---
        campaign_operation = googleads_client.get_type("CampaignOperation")
        campaign = campaign_operation.create
        campaign.name = f"LocalVortex Campaign for {business.business_name}"
        campaign.advertising_channel_type = googleads_client.enums.AdvertisingChannelTypeEnum.SEARCH
        campaign.status = googleads_client.enums.CampaignStatusEnum.PAUSED # Start paused
        campaign.manual_cpc.enhanced_cpc_enabled = True
        campaign.campaign_budget = budget_resource_name
        campaign.network_settings.target_google_search = True
        campaign.network_settings.target_search_network = True
        campaign_response = campaign_service.mutate_campaigns(
            customer_id=customer_id, operations=[campaign_operation]
        )
        campaign_resource_name = campaign_response.results[0].resource_name
        print(f"Created campaign: {campaign_resource_name}")

        # --- 3. Create an Ad Group ---
        ad_group_operation = googleads_client.get_type("AdGroupOperation")
        ad_group = ad_group_operation.create
        ad_group.name = f"{business.specialties.split(',')[0].strip()} Ad Group"
        ad_group.status = googleads_client.enums.AdGroupStatusEnum.ENABLED
        ad_group.campaign = campaign_resource_name
        ad_group_response = ad_group_service.mutate_ad_groups(
            customer_id=customer_id, operations=[ad_group_operation]
        )
        ad_group_resource_name = ad_group_response.results[0].resource_name
        print(f"Created ad group: {ad_group_resource_name}")

        # --- 4. Create Keywords ---
        keywords = [f"{s.strip()} {business.service_area}" for s in business.specialties.split(',')]
        keyword_operations = []
        for keyword_text in keywords:
            keyword_op = googleads_client.get_type("AdGroupCriterionOperation")
            criterion = keyword_op.create
            criterion.ad_group = ad_group_resource_name
            criterion.keyword.text = keyword_text
            criterion.keyword.match_type = googleads_client.enums.KeywordMatchTypeEnum.BROAD
            keyword_operations.append(keyword_op)

        ad_group_criterion_service.mutate_ad_group_criteria(
            customer_id=customer_id, operations=keyword_operations,
        )
        print(f"Created {len(keywords)} keywords.")

        # --- 5. Create a Responsive Search Ad ---
        ad_op = googleads_client.get_type("AdGroupAdOperation")
        ad_group_ad = ad_op.create
        ad_group_ad.ad_group = ad_group_resource_name
        ad_group_ad.status = googleads_client.enums.AdGroupAdStatusEnum.PAUSED
        ad_group_ad.ad.final_urls.append("https://example.com") # Placeholder URL

        # Populate headlines
        for headline in ad_copy['headlines']:
            ad_group_ad.ad.responsive_search_ad.headlines.append(
                googleads_client.get_type("AdTextAsset", text=headline)
            )
        # Populate descriptions
        for description in ad_copy['descriptions']:
            ad_group_ad.ad.responsive_search_ad.descriptions.append(
                googleads_client.get_type("AdTextAsset", text=description)
            )

        ad_group_ad_service.mutate_ad_group_ads(
            customer_id=customer_id, operations=[ad_op]
        )
        print("Created responsive search ad.")

        # --- Update status and save ---
        business.campaign_status = "Active - Paused"
        db.session.commit()
        print(f"Successfully created campaign for {business.business_name}.")

    except GoogleAdsException as ex:
        print(
            f'Request with ID "{ex.request_id}" failed with status'
            f'"{ex.error.code().name}" and includes the following errors:'
        )
        for error in ex.failure.errors:
            print(f'\tError with message "{error.message}".')
            if error.location:
                for field_path_element in error.location.field_path_elements:
                    print(f"\t\tOn field: {field_path_element.field_name}")
        business.campaign_status = "Failed: Google Ads API Error"
        db.session.commit()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        business.campaign_status = "Failed: Unexpected Error"
        db.session.commit()

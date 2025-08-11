import os
import uuid
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
import google.generativeai as genai
from .extensions import db
from flask import current_app


def generate_ad_copy_with_gemini(business):
    """
    Generates ad copy using the Gemini API.
    """
    current_app.logger.info(f"Generating ad copy with Gemini for {business.business_name}...")
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
        lines = response.text.strip().split('\n')
        headlines = [l for l in lines if l.startswith('Headline')][:5]
        descriptions = [l for l in lines if l.startswith('Description')][:3]

        headlines = [h.split(': ')[1].strip('"') for h in headlines]
        descriptions = [d.split(': ')[1].strip('"') for d in descriptions]

        return {"headlines": headlines, "descriptions": descriptions}

    except Exception as e:
        current_app.logger.error(f"Error generating Gemini ad copy for {business.business_name}: {e}")
        return None


def manage_ad_campaign(business, budget_micros):
    """
    Creates and manages a Google Ads campaign for a business.
    """
    current_app.logger.info(f"Starting ad campaign management for {business.business_name}...")

    try:
        googleads_client = GoogleAdsClient.load_from_env()
        customer_id = business.google_ads_customer_id

        ad_copy = generate_ad_copy_with_gemini(business)
        if not ad_copy or len(ad_copy['headlines']) < 3 or len(ad_copy['descriptions']) < 2:
            current_app.logger.error("Failed to generate sufficient ad copy. Aborting campaign creation.")
            business.campaign_status = "Failed: Ad Copy Generation"
            db.session.commit()
            return

        campaign_service = googleads_client.get_service("CampaignService")
        ad_group_service = googleads_client.get_service("AdGroupService")
        ad_group_ad_service = googleads_client.get_service("AdGroupAdService")
        ad_group_criterion_service = googleads_client.get_service("AdGroupCriterionService")
        campaign_budget_service = googleads_client.get_service("CampaignBudgetService")

        budget_operation = googleads_client.get_type("CampaignBudgetOperation")
        campaign_budget = budget_operation.create
        campaign_budget.name = f"Budget for {business.business_name} {uuid.uuid4()}"
        campaign_budget.delivery_method = googleads_client.enums.BudgetDeliveryMethodEnum.STANDARD
        campaign_budget.amount_micros = budget_micros
        budget_response = campaign_budget_service.mutate_campaign_budgets(
            customer_id=customer_id, operations=[budget_operation]
        )
        budget_resource_name = budget_response.results[0].resource_name
        current_app.logger.info(f"Created campaign budget: {budget_resource_name}")

        campaign_operation = googleads_client.get_type("CampaignOperation")
        campaign = campaign_operation.create
        campaign.name = f"LocalVortex Campaign for {business.business_name}"
        campaign.advertising_channel_type = googleads_client.enums.AdvertisingChannelTypeEnum.SEARCH
        campaign.status = googleads_client.enums.CampaignStatusEnum.PAUSED
        campaign.manual_cpc.enhanced_cpc_enabled = True
        campaign.campaign_budget = budget_resource_name
        campaign.network_settings.target_google_search = True
        campaign.network_settings.target_search_network = True
        campaign_response = campaign_service.mutate_campaigns(
            customer_id=customer_id, operations=[campaign_operation]
        )
        campaign_resource_name = campaign_response.results[0].resource_name
        current_app.logger.info(f"Created campaign: {campaign_resource_name}")

        ad_group_operation = googleads_client.get_type("AdGroupOperation")
        ad_group = ad_group_operation.create
        ad_group.name = f"{business.specialties.split(',')[0].strip()} Ad Group"
        ad_group.status = googleads_client.enums.AdGroupStatusEnum.ENABLED
        ad_group.campaign = campaign_resource_name
        ad_group_response = ad_group_service.mutate_ad_groups(
            customer_id=customer_id, operations=[ad_group_operation]
        )
        ad_group_resource_name = ad_group_response.results[0].resource_name
        current_app.logger.info(f"Created ad group: {ad_group_resource_name}")

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
        current_app.logger.info(f"Created {len(keywords)} keywords.")

        ad_op = googleads_client.get_type("AdGroupAdOperation")
        ad_group_ad = ad_op.create
        ad_group_ad.ad_group = ad_group_resource_name
        ad_group_ad.status = googleads_client.enums.AdGroupAdStatusEnum.PAUSED
        ad_group_ad.ad.final_urls.append("https://example.com")

        for headline in ad_copy['headlines']:
            ad_group_ad.ad.responsive_search_ad.headlines.append(
                googleads_client.get_type("AdTextAsset", text=headline)
            )
        for description in ad_copy['descriptions']:
            ad_group_ad.ad.responsive_search_ad.descriptions.append(
                googleads_client.get_type("AdTextAsset", text=description)
            )

        ad_group_ad_service.mutate_ad_group_ads(
            customer_id=customer_id, operations=[ad_op]
        )
        current_app.logger.info("Created responsive search ad.")

        business.campaign_status = "Active - Paused"
        db.session.commit()
        current_app.logger.info(f"Successfully created campaign for {business.business_name}.")

    except GoogleAdsException as ex:
        current_app.logger.error(f'Google Ads API request with ID "{ex.request_id}" failed.')
        for error in ex.failure.errors:
            current_app.logger.error(f'\tError with message "{error.message}".')
            if error.location:
                for field_path_element in error.location.field_path_elements:
                    current_app.logger.error(f"\t\tOn field: {field_path_element.field_name}")
        business.campaign_status = "Failed: Google Ads API Error"
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred during ad campaign creation: {e}")
        business.campaign_status = "Failed: Unexpected Error"
        db.session.commit()

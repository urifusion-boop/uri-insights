from app.domain.enums.ai_prompt import LeadFormAutoPopulateEnum
from app.domain.enums.leadform_enum import (
    LeadFormTypeEnum,
)
from app.domain.schemas.leadform_schema import (
    ConversationalLeadFormUpdate,
    GoogleMapsLeadFormUpdate,
    LeadFormUpdateBase,
    OrganizationLeadFormUpdate,
    PersonLeadFormUpdate,
)


class LeadFormHelper:
    FORM_TYPE_TO_PROMPT_MAP = {
        LeadFormTypeEnum.ORGANIZATION: LeadFormAutoPopulateEnum.ORGANIZATION_FORM_PROMPT.value,
        LeadFormTypeEnum.PERSON: LeadFormAutoPopulateEnum.PERSON_FORM_PROMPT.value,
        LeadFormTypeEnum.CONVERSATIONAL: LeadFormAutoPopulateEnum.CONVERSATIONAL_FORM_PROMPT.value,
        LeadFormTypeEnum.GOOGLE_MAPS: LeadFormAutoPopulateEnum.GOOGLE_MAPS_FORM_PROMPT.value,
    }

    FORM_TYPE_TO_RESULT_MODEL_MAP = {
        LeadFormTypeEnum.ORGANIZATION: OrganizationLeadFormUpdate,
        LeadFormTypeEnum.PERSON: PersonLeadFormUpdate,
        LeadFormTypeEnum.CONVERSATIONAL: ConversationalLeadFormUpdate,
        LeadFormTypeEnum.GOOGLE_MAPS: GoogleMapsLeadFormUpdate,
    }

    DEFAULT_ERR_MESSAGE = "Invalid form type provided for auto population."

    @staticmethod
    def get_prompt_for_auto_population(lead_form_type: LeadFormTypeEnum):
        result = LeadFormHelper.FORM_TYPE_TO_PROMPT_MAP.get(lead_form_type)
        return LeadFormHelper._handle_result(result)

    @staticmethod
    def get_result_model_for_auto_population(lead_form_type: LeadFormTypeEnum):
        result = LeadFormHelper.FORM_TYPE_TO_RESULT_MODEL_MAP.get(lead_form_type)
        return LeadFormHelper._handle_result(result)

    @staticmethod
    def _handle_result(result):
        if not result:
            raise ValueError(LeadFormHelper.DEFAULT_ERR_MESSAGE)
        return result

    @staticmethod
    def process_auto_generated_inputs(lead_form_input: LeadFormUpdateBase):
        lead_form_input.page = 1
        lead_form_input.per_page = 10
        return lead_form_input

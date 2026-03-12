from app.database import get_db
from app.repository.EmbeddingRepository import EmbeddingRepository
from app.repository.LeadFormRepository import LeadFormRepository
from app.repository.LeadRepository import LeadRepository
from app.repository.LeadSearchHistoryRepository import LeadSearchHistoryRepository
from app.repository.LeadGenerationJobRepository import LeadGenerationJobRepository
from app.services.azure.consumers.FileImportConsumer import FileImportConsumer
from app.services.azure.consumers.LeadProcessorConsumer import LeadProcessorConsumer
from app.services.azure.consumers.NewSubscriptionConsumer import NewSubscriptionConsumer
from motor.motor_asyncio import AsyncIOMotorDatabase


async def start_service_bus_consumers():
    await NewSubscriptionConsumer.create()
    await FileImportConsumer.create()
    await LeadProcessorConsumer.create()


async def run_db_startup_tasks():
    db: AsyncIOMotorDatabase = get_db()
    try:
        await EmbeddingRepository.create_vector_index(db)
        await LeadSearchHistoryRepository.setup_indexes(db)
        await LeadGenerationJobRepository.ensure_indexes(db)
    except Exception as e:
        print(f"[startup] DB startup tasks failed (non-fatal): {e}")
    # await LeadRepository.update_conv_to_biz_leads(db)
    # await LeadFormRepository.change_conversational_lead_forms_to_business_lead_forms(db)
    # await LeadRepository.delete_duplicate_leads(get_db())


async def shutdown_service_bus_consumers():
    await NewSubscriptionConsumer.shutdown()
    await FileImportConsumer.shutdown()
    await LeadProcessorConsumer.shutdown()

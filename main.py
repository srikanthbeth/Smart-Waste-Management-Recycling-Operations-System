from fastapi import FastAPI

from core.config import settings

from routes.auth import router as auth_router
from routes.users import router as users_router
from routes.locations import router as locations_router
from routes.waste_categories import router as waste_categories_router
from routes.customers import router as customers_router
from routes.pickups import router as pickups_router
from routes.vehicles import router as vehicles_router
from routes.drivers import router as drivers_router
from routes.field_workers import router as field_workers_router

from routes.collection_assignments import (
    router as collection_assignments_router,
)

from routes.collection_trackings import (
    router as collection_trackings_router,
)

from routes.recycling_centers import (
    router as recycling_centers_router,
)

from routes.waste_transfers import (
    router as waste_transfers_router,
)

from routes.waste_segregations import (
    router as waste_segregations_router,
)

from routes.waste_processings import (
    router as waste_processings_router,
)

from routes.waste_disposals import router as waste_disposals_router

from routes.vehicle_maintenances import router as vehicle_maintenances_router
from routes.customer_complaints import router as customer_complaints_router
from routes.collection_performance import (
    router as collection_performance_router,
)

from routes.environmental_impact import (
    router as environmental_impact_router,
)
from routes.admin_dashboard import router as admin_dashboard_router
from routes.advanced_reports import router as advanced_reports_router

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Smart Waste Management & Recycling Operations System API"
    ),
    version="1.0.0",
)


# Authentication
app.include_router(auth_router)

# User management
app.include_router(users_router)

# Location management
app.include_router(locations_router)

# Waste categories
app.include_router(waste_categories_router)

# Customer management
app.include_router(customers_router)

# Pickup management
app.include_router(pickups_router)

# Vehicle management
app.include_router(vehicles_router)

# Driver and field worker management
app.include_router(drivers_router)
app.include_router(field_workers_router)

# Collection assignments
app.include_router(collection_assignments_router)

# Collection tracking
app.include_router(collection_trackings_router)

# Recycling center management
app.include_router(recycling_centers_router)

# Waste transfer management
app.include_router(waste_transfers_router)

# Waste segregation management
app.include_router(waste_segregations_router)

app.include_router(waste_processings_router)


app.include_router(waste_disposals_router)

app.include_router(vehicle_maintenances_router)



app.include_router(customer_complaints_router)


# Collection performance analytics
app.include_router(collection_performance_router)

app.include_router(environmental_impact_router)


app.include_router(admin_dashboard_router)

app.include_router(advanced_reports_router)



@app.get("/", tags=["Health"])
def root():
    return {
        "message": "Smart Waste Management API is running",
        "status": "success",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
    }
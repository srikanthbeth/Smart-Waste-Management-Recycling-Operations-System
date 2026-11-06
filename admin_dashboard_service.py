from datetime import datetime, timezone

from sqlalchemy.orm import Session

from repositories.admin_dashboard_repository import (
    get_total_customers,
    get_collection_statistics,
    get_vehicle_statistics,
    get_recycling_statistics,
    get_complaint_statistics,
    get_maintenance_statistics,
)

from schemas.admin_dashboard import (
    AdminDashboardResponse,
    CollectionDashboard,
    VehicleDashboard,
    RecyclingDashboard,
    ComplaintDashboard,
    MaintenanceDashboard,
    DashboardSummaryResponse,
)


def get_admin_dashboard(db: Session) -> AdminDashboardResponse:
    total_customers = get_total_customers(db)

    collection_data = get_collection_statistics(db)
    vehicle_data = get_vehicle_statistics(db)
    recycling_data = get_recycling_statistics(db)
    complaint_data = get_complaint_statistics(db)
    maintenance_data = get_maintenance_statistics(db)

    return AdminDashboardResponse(
        total_customers=total_customers,
        collections=CollectionDashboard(**collection_data),
        vehicles=VehicleDashboard(**vehicle_data),
        recycling=RecyclingDashboard(**recycling_data),
        complaints=ComplaintDashboard(**complaint_data),
        maintenance=MaintenanceDashboard(**maintenance_data),
        generated_at=datetime.now(timezone.utc).date(),
    )


def get_dashboard_summary(db: Session) -> DashboardSummaryResponse:
    dashboard = get_admin_dashboard(db)

    return DashboardSummaryResponse(
        total_customers=dashboard.total_customers,

        total_collection_requests=(
            dashboard.collections.total_collection_requests
        ),

        completed_collections=(
            dashboard.collections.completed_collections
        ),

        pending_pickups=(
            dashboard.collections.pending_pickups
        ),

        missed_collections=(
            dashboard.collections.missed_collections
        ),

        total_vehicles=dashboard.vehicles.total_vehicles,

        available_vehicles=(
            dashboard.vehicles.available_vehicles
        ),

        active_recycling_centers=(
            dashboard.recycling.active_recycling_centers
        ),

        total_waste_collected_kg=(
            dashboard.recycling.total_waste_collected_kg
        ),

        total_waste_recycled_kg=(
            dashboard.recycling.total_waste_recycled_kg
        ),

        recycling_efficiency_percentage=(
            dashboard.recycling.recycling_efficiency_percentage
        ),

        pending_complaints=(
            dashboard.complaints.pending_complaints
        ),

        maintenance_status={
            "total": dashboard.maintenance.total_maintenance_records,
            "pending": dashboard.maintenance.pending_maintenance,
            "in_progress": dashboard.maintenance.in_progress_maintenance,
            "completed": dashboard.maintenance.completed_maintenance,
            "overdue": dashboard.maintenance.overdue_maintenance,
        },
    )
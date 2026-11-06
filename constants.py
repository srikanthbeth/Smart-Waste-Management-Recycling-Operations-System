
from enum import Enum


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    OPERATIONS_MANAGER = "operations_manager"
    COLLECTION_SUPERVISOR = "collection_supervisor"
    DRIVER = "driver"
    RECYCLING_CENTER_MANAGER = "recycling_center_manager"
    FIELD_WORKER = "field_worker"
    CUSTOMER = "customer"


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    PASSWORD_RESET = "password_reset"


class LocationType(str, Enum):
    ZONE = "zone"
    WARD = "ward"
    AREA = "area"
    COLLECTION_POINT = "collection_point"
    RECYCLING_CENTER = "recycling_center"


class LocationStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class WasteCategoryStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class CustomerType(str, Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    INSTITUTIONAL = "institutional"


class CustomerStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class PropertyType(str, Enum):
    HOUSE = "house"
    APARTMENT = "apartment"
    SHOP = "shop"
    OFFICE = "office"
    FACTORY = "factory"
    OTHER = "other"




class PickupStatus(str, Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class PickupPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class VehicleType(str, Enum):
    TRUCK = "truck"
    MINI_TRUCK = "mini_truck"
    COMPACTOR = "compactor"
    TIPPER = "tipper"
    TRACTOR = "tractor"
    OTHER = "other"


class FuelType(str, Enum):
    DIESEL = "diesel"
    PETROL = "petrol"
    CNG = "cng"
    ELECTRIC = "electric"
    HYBRID = "hybrid"
    OTHER = "other"


class VehicleStatus(str, Enum):
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    IN_SERVICE = "in_service"
    MAINTENANCE = "maintenance"
    OUT_OF_SERVICE = "out_of_service"
    RETIRED = "retired"

class StaffStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_LEAVE = "on_leave"
    SUSPENDED = "suspended"


class StaffAvailability(str, Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    UNAVAILABLE = "unavailable"

class AssignmentStatus(str, Enum):
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class CollectionTrackingStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"

class RecyclingCenterStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"

class WasteTransferStatus(str, Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    IN_TRANSIT = "in_transit"
    RECEIVED = "received"
    PARTIALLY_RECEIVED = "partially_received"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class WasteSegregationStatus(str, Enum):
    COMPLETED = "completed"
    PARTIALLY_SEGREGATED = "partially_segregated"


class WasteProcessingStatus(str, Enum):
    COMPLETED = "completed"
    PARTIALLY_PROCESSED = "partially_processed"


class WasteProcessingMethod(str, Enum):
    COMPOSTING = "composting"
    SHREDDING = "shredding"
    BALING = "baling"
    MELTING = "melting"
    MATERIAL_RECOVERY = "material_recovery"
    ANAEROBIC_DIGESTION = "anaerobic_digestion"
    OTHER = "other"


class WasteProcessingResult(str, Enum):
    RECYCLABLE_OUTPUT = "recyclable_output"
    RESIDUAL_WASTE = "residual_waste"
    PROCESSING_LOSS = "processing_loss"

class WasteDisposalMethod(str, Enum):
    LANDFILL = "landfill"
    INCINERATION = "incineration"
    SECURE_LANDFILL = "secure_landfill"
    DEEP_BURIAL = "deep_burial"
    OTHER = "other"


class WasteDisposalStatus(str, Enum):
    COMPLETED = "completed"
    PARTIALLY_DISPOSED = "partially_disposed"

from enum import Enum


class MaintenanceType(str, Enum):
    PREVENTIVE = "preventive"
    CORRECTIVE = "corrective"
    BREAKDOWN = "breakdown"
    INSPECTION = "inspection"
    EMERGENCY = "emergency"
    OTHER = "other"


class MaintenanceStatus(str, Enum):
    REQUESTED = "requested"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MaintenancePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ComplaintCategory(str, Enum):
    MISSED_PICKUP = "missed_pickup"
    DELAYED_PICKUP = "delayed_pickup"
    WASTE_NOT_COLLECTED = "waste_not_collected"
    VEHICLE_ISSUE = "vehicle_issue"
    STAFF_BEHAVIOUR = "staff_behaviour"
    BILLING_ISSUE = "billing_issue"
    OTHER = "other"


class ComplaintPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplaintStatus(str, Enum):
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REJECTED = "rejected"
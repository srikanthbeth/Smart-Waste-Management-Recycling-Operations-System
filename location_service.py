
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.constants import LocationStatus, LocationType
from models.location import Location
from repositories.location_repository import LocationRepository


class LocationService:

    @staticmethod
    def create_location(
        db: Session,
        location_data: dict,
    ) -> Location:

        code = location_data["code"].strip().upper()

        existing = LocationRepository.get_by_code(db, code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Location code already exists",
            )

        location_data["code"] = code

        parent_id = location_data.get("parent_id")

        if parent_id:
            parent = LocationRepository.get_by_id(db, parent_id)

            if not parent:
                raise HTTPException(
                    status_code=404,
                    detail="Parent location not found",
                )

            if parent.status != LocationStatus.ACTIVE:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot assign an inactive parent location",
                )

        LocationService.validate_parent_type(
            db,
            location_data["location_type"],
            parent_id,
        )

        try:
            return LocationRepository.create(db, location_data)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Location code already exists",
            )

    @staticmethod
    def validate_parent_type(
        db: Session,
        location_type: LocationType,
        parent_id: UUID | None,
    ) -> None:

        if parent_id is None:
            if location_type != LocationType.ZONE:
                raise HTTPException(
                    status_code=400,
                    detail="Only a zone can be created without a parent",
                )
            return

        parent = LocationRepository.get_by_id(db, parent_id)

        allowed_parents = {
            LocationType.WARD: [LocationType.ZONE],
            LocationType.AREA: [LocationType.WARD],
            LocationType.COLLECTION_POINT: [LocationType.AREA],
            LocationType.RECYCLING_CENTER: [
                LocationType.ZONE,
                LocationType.AREA,
            ],
            LocationType.ZONE: [],
        }

        if parent.location_type not in allowed_parents[location_type]:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid parent type for {location_type.value}"
                ),
            )

    @staticmethod
    def get_location(
        db: Session,
        location_id: UUID,
    ) -> Location:

        location = LocationRepository.get_by_id(db, location_id)

        if not location:
            raise HTTPException(
                status_code=404,
                detail="Location not found",
            )

        return location

    @staticmethod
    def list_locations(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        location_type=None,
        status_filter=None,
        parent_id=None,
    ) -> list[Location]:

        return LocationRepository.list_all(
            db=db,
            skip=skip,
            limit=limit,
            location_type=location_type,
            status=status_filter,
            parent_id=parent_id,
        )

    @staticmethod
    def update_location(
        db: Session,
        location_id: UUID,
        update_data: dict,
    ) -> Location:

        location = LocationService.get_location(db, location_id)

        if "parent_id" in update_data:
            new_parent_id = update_data["parent_id"]

            if new_parent_id == location.id:
                raise HTTPException(
                    status_code=400,
                    detail="A location cannot be its own parent",
                )

            if new_parent_id is not None:
                parent = LocationRepository.get_by_id(
                    db,
                    new_parent_id,
                )

                if not parent:
                    raise HTTPException(
                        status_code=404,
                        detail="Parent location not found",
                    )

                if parent.status != LocationStatus.ACTIVE:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot assign an inactive parent location",
                    )

            new_type = update_data.get(
                "location_type",
                location.location_type,
            )

            LocationService.validate_parent_type(
                db,
                new_type,
                new_parent_id,
            )

        elif "location_type" in update_data:
            LocationService.validate_parent_type(
                db,
                update_data["location_type"],
                location.parent_id,
            )

        if "latitude" in update_data or "longitude" in update_data:
            latitude = update_data.get(
                "latitude",
                location.latitude,
            )
            longitude = update_data.get(
                "longitude",
                location.longitude,
            )

            if (latitude is None) != (longitude is None):
                raise HTTPException(
                    status_code=400,
                    detail="Latitude and longitude must be provided together",
                )

        return LocationRepository.update(
            db,
            location,
            update_data,
        )

    @staticmethod
    def update_location_status(
        db: Session,
        location_id: UUID,
        new_status: LocationStatus,
    ) -> Location:

        location = LocationService.get_location(db, location_id)

        if new_status == LocationStatus.INACTIVE:
            if LocationRepository.has_children(db, location_id):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Cannot deactivate a location that has child locations"
                    ),
                )

        location.status = new_status
        location.is_active = new_status == LocationStatus.ACTIVE

        db.commit()
        db.refresh(location)

        return location

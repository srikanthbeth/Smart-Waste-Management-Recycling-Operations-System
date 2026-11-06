# Smart Waste Management & Recycling Operations System

## Project Overview

The **Smart Waste Management & Recycling Operations System** is an advanced backend application developed using FastAPI and PostgreSQL. It is designed to manage waste collection operations, vehicle assignments, waste segregation, recycling activities, disposal management, and environmental impact tracking.

The system provides role-based access control and RESTful APIs to support administrators, operations managers, supervisors, drivers, field workers, recycling center managers, and customers.

## Technologies Used

- **Programming Language:** Python 3.11+
- **Backend Framework:** FastAPI
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Data Validation:** Pydantic
- **Authentication:** JWT
- **Password Security:** Passlib / bcrypt
- **Database Migrations:** Alembic
- **Testing:** Pytest
- **API Documentation:** Swagger UI / OpenAPI
- **Environment Management:** Python Virtual Environment
- **Version Control:** Git

## Key Features

### 1. Authentication and Authorization
- User registration and login
- JWT access token authentication
- Password hashing
- Role-based access control
- Secure API endpoints

### 2. Location Management
- Manage collection zones and locations
- Create, update, and retrieve location information
- Track location status

### 3. Waste Category Management
- Create and manage waste categories
- Classify recyclable and non-recyclable waste
- Maintain waste category information

### 4. Customer Management
- Customer registration and management
- Customer profile management
- Customer-related pickup operations

### 5. Pickup Management
- Create and manage pickup requests
- Track pickup status and priority
- Manage pickup scheduling

### 6. Vehicle Management
- Register collection vehicles
- Maintain vehicle information
- Track vehicle availability and status

### 7. Driver and Field Worker Management
- Driver registration and management
- Field worker management
- Assign operational responsibilities

### 8. Collection Assignment Management
- Assign drivers and vehicles to pickups
- Manage collection assignments
- Track assignment status

### 9. Collection Tracking
- Track collection activities
- Record collection progress
- Maintain collection status updates

### 10. Recycling Center Management
- Register recycling centers
- Manage recycling center information
- Track center operations

### 11. Waste Transfer Management
- Manage waste transfers
- Track transfer quantities
- Maintain transfer status

### 12. Waste Segregation
- Record waste segregation activities
- Categorize waste materials
- Track segregated waste quantities

### 13. Waste Processing
- Manage waste processing activities
- Record input and output quantities
- Track processing results

### 14. Disposal Management
- Record waste disposal activities
- Track disposal quantities and methods
- Maintain disposal records

### 15. Vehicle Maintenance
- Manage vehicle maintenance records
- Track maintenance schedules
- Monitor vehicle maintenance status

### 16. Service Complaint Management
- Register service complaints
- Track complaint status
- Manage complaint resolution

### 17. Collection Performance Analytics
- Monitor collection performance
- Generate operational performance statistics
- Track driver and vehicle performance

### 18. Environmental Impact Tracking
- Track collected and recycled waste
- Calculate recycling rates
- Monitor environmental impact metrics

### 19. Admin Dashboard
- View operational summaries
- Monitor collection activities
- Track vehicle and recycling performance
- View complaint and maintenance statistics

### 20. Advanced Reports
- Daily collection reports
- Monthly collection reports
- Zone-wise performance reports
- Driver performance reports
- Vehicle utilization reports
- Waste category reports
- Recycling center performance reports
- Recycling yield reports
- Disposal reports
- Environmental impact reports
- Filtering, sorting, and pagination

### 21. Audit Logs
- Maintain records of important system activities
- Track user actions
- Record affected entities
- Support activity monitoring and accountability

## User Roles

The system supports the following roles:

1. Super Admin
2. Operations Manager
3. Collection Supervisor
4. Driver
5. Recycling Center Manager
6. Field Worker
7. Customer

Each role has specific permissions to access and manage system resources.

## Project Structure

```text
smart_waste_management/
│
├── core/
│   ├── config.py
│   ├── constants.py
│   ├── exceptions.py
│   ├── permissions.py
│   └── security.py
│
├── db/
│   ├── base.py
│   └── session.py
│
├── models/
│   ├── user.py
│   ├── location.py
│   ├── pickup.py
│   ├── vehicle.py
│   ├── driver.py
│   ├── recycling_center.py
│   └── ...
│
├── schemas/
│   └── ...
│
├── repositories/
│   └── ...
│
├── services/
│   └── ...
│
├── routes/
│   └── ...
│
├── tests/
│   ├── test_auth.py
│   ├── test_locations.py
│   ├── test_customers.py
│   ├── test_pickups.py
│   └── ...
│
├── alembic/
│   └── versions/
│
├── .env
├── .env.example
├── .gitignore
├── alembic.ini
├── main.py
└── README.md
```

## Installation and Setup

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd smart_waste_management
```

### 2. Create a Virtual Environment

```powershell
python -m venv .venv
```

### 3. Activate the Virtual Environment

```powershell
.venv\Scripts\Activate.ps1
```

### 4. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a `.env` file in the project root directory.

Example:

```env
APP_NAME=Smart Waste Management & Recycling Operations System
ENVIRONMENT=development
DEBUG=True

DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5433/smart_waste_management

TEST_DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5433/smart_waste_management_test

JWT_SECRET_KEY=YOUR_SECRET_KEY
JWT_ALGORITHM=HS256

ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

Replace the database credentials and JWT secret with your own values. Do not commit `.env` to Git.

### 6. Run Database Migrations

```powershell
alembic upgrade head
```

### 7. Start the Application

```powershell
uvicorn main:app --reload
```

The application will run at:

`http://127.0.0.1:8000`

## API Documentation

FastAPI automatically generates interactive API documentation.

**Swagger UI:**

`http://127.0.0.1:8000/docs`

**ReDoc:**

`http://127.0.0.1:8000/redoc`

## Testing

The project uses Pytest for automated testing.

Run the complete test suite:

```powershell
python -m pytest -v
```

Run tests with a summary:

```powershell
python -m pytest -q
```

Run an individual test file:

```powershell
python -m pytest .\tests\test_auth.py -v
```

### Test Results

**Total Tests Passed: 490**

The automated test suite covers:

- Authentication and authorization
- Role-based access control
- CRUD operations
- Data validation
- Pickup and collection management
- Vehicle and driver management
- Waste segregation and processing
- Recycling and disposal operations
- Maintenance and complaints
- Environmental impact tracking
- Dashboard and advanced reports
- API response validation
- Access restrictions and error handling

## Database Management

PostgreSQL is used as the primary database.

Alembic manages database schema changes and migrations.

Useful commands:

```powershell
alembic revision --autogenerate -m "migration description"
```

```powershell
alembic upgrade head
```

```powershell
alembic current
```

```powershell
alembic history
```

## Main Workflow

The primary operational workflow is:

1. Administrator logs into the system.
2. Creates collection zones.
3. Registers customers.
4. Creates waste pickup requests.
5. Assigns vehicles and drivers.
6. Tracks collection activities.
7. Transfers collected waste to recycling centers.
8. Records waste segregation.
9. Processes recyclable waste.
10. Records waste disposal.
11. Calculates environmental impact.
12. Views dashboard statistics and reports.
13. Reviews audit logs.

## Security Features

- JWT-based authentication
- Secure password hashing
- Role-based authorization
- Protected API endpoints
- Input validation using Pydantic
- Environment-based configuration
- Separate development and testing databases
- Audit trail for system activities

## Future Enhancements

- GPS-based vehicle tracking
- Real-time collection notifications
- Route optimization
- Mobile application integration
- IoT-enabled smart waste bins
- Predictive waste generation analytics
- Advanced environmental reporting

## Conclusion

The Smart Waste Management & Recycling Operations System provides a structured backend solution for managing waste collection, transportation, recycling, processing, and disposal operations.

It demonstrates the practical implementation of FastAPI, PostgreSQL, SQLAlchemy, Alembic, JWT authentication, role-based access control, RESTful API development, and automated testing.

**Project Status:** Development and testing completed for the implemented modules.

**Automated Test Results:** 490 tests passed.
AUTHOR 
BETHAMCHARLA SRIKANTH

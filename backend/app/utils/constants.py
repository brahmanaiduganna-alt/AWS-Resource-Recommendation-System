CATEGORY_INFO = [
    {"name": "E-Commerce", "description": "Online stores with catalogs, carts and payments. Needs a reliable database and handles traffic spikes."},
    {"name": "AI/ML", "description": "Model training or inference APIs. Often needs more CPU and RAM, or a GPU instance."},
    {"name": "Website Hosting", "description": "Static or dynamic websites and blogs. Usually light compute with CDN delivery."},
    {"name": "Mobile App", "description": "Backend APIs, authentication and storage for iOS and Android apps."},
    {"name": "Video Streaming", "description": "Video upload, storage and delivery. Storage and data transfer dominate the cost."},
    {"name": "IoT", "description": "Many devices sending small messages continuously. Needs ingestion and time-series storage."},
    {"name": "Database", "description": "Relational or NoSQL workloads where memory, storage and IOPS matter."},
    {"name": "DevOps", "description": "CI/CD runners, build servers and internal tooling."},
    {"name": "Data Analytics", "description": "Batch processing, ETL and reporting on large datasets."},
    {"name": "Serverless", "description": "Event-driven functions and APIs where you pay per request."},
]

CATEGORIES = [c["name"] for c in CATEGORY_INFO]

REGIONS = [
    {"code": "ap-south-1", "name": "Asia Pacific (Mumbai)"},
    {"code": "ap-south-2", "name": "Asia Pacific (Hyderabad)"},
    {"code": "ap-southeast-1", "name": "Asia Pacific (Singapore)"},
    {"code": "ap-southeast-2", "name": "Asia Pacific (Sydney)"},
    {"code": "ap-northeast-1", "name": "Asia Pacific (Tokyo)"},
    {"code": "us-east-1", "name": "US East (N. Virginia)"},
    {"code": "us-east-2", "name": "US East (Ohio)"},
    {"code": "us-west-1", "name": "US West (N. California)"},
    {"code": "us-west-2", "name": "US West (Oregon)"},
    {"code": "eu-west-1", "name": "Europe (Ireland)"},
    {"code": "eu-west-2", "name": "Europe (London)"},
    {"code": "eu-central-1", "name": "Europe (Frankfurt)"},
]

PERFORMANCE_LEVELS = ["low", "medium", "high"]

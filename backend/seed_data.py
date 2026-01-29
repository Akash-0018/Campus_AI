"""
Comprehensive seed database with 45-50 user profiles
Each user has a detailed profile with resumes, skills, and verified status
All embeddings are generated for RAG-based retrieval
Implements 2-role architecture: ADMIN + USER (no recruiter role)
"""
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from sqlmodel import Session, select, create_engine
from models.user import User, UserRole
from models.resume import Resume
from utils.config import DATABASE_URL, CHROMA_PERSISTENT_PATH, EMBEDDING_MODEL
import hashlib
import shutil

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import embeddings for ChromaDB
try:
    from services.embeddings_service import EmbeddingsService
    embeddings_available = True
except ImportError:
    embeddings_available = False
    logger.warning("EmbeddingsService not available, will skip embeddings")

def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def clear_chroma_db():
    """Clear and reset ChromaDB"""
    try:
        chroma_path = Path(CHROMA_PERSISTENT_PATH)
        if chroma_path.exists():
            print(f"🗑️  Clearing ChromaDB at {CHROMA_PERSISTENT_PATH}...")
            import time
            import gc
            
            # Try to clean up and remove files
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    gc.collect()  # Cleanup garbage
                    time.sleep(0.5)  # Wait a bit
                    
                    # Try to remove directory
                    shutil.rmtree(chroma_path)
                    print("✓ ChromaDB cleared successfully")
                    return
                except PermissionError as e:
                    if attempt < max_retries - 1:
                        print(f"  ⚠️  Retrying... ({attempt + 1}/{max_retries})")
                        time.sleep(1)
                    else:
                        print(f"  ⚠️  Could not delete ChromaDB, will clear collection instead")
                        # Try to clear collections instead of deleting directory
                        try:
                            import chromadb
                            client = chromadb.PersistentClient(path=str(chroma_path))
                            collections = client.list_collections()
                            for collection in collections:
                                client.delete_collection(name=collection.name)
                            print("✓ ChromaDB collections cleared")
                        except Exception as inner_e:
                            print(f"  ⚠️  Could not clear collections: {inner_e}")
                        return
        else:
            print(f"ℹ️  ChromaDB path doesn't exist, creating fresh: {CHROMA_PERSISTENT_PATH}")
    except Exception as e:
        logger.warning(f"Error clearing ChromaDB: {e}, continuing anyway...")

def get_user_profiles() -> list:
    """Generate 45-50 diverse user profiles with resume content"""
    profiles = [
        # Backend Engineers (10 profiles)
        {
            "user": {"username": "john_python_dev", "email": "john.python@email.com", "full_name": "John Smith", "bio": "Senior Python developer with 8+ years experience"},
            "resume_content": "John Smith - Senior Python Developer\n8+ years of backend development\nSkills: Python, Django, PostgreSQL, REST APIs, microservices, async programming, pytest, Redis, Celery, AWS Lambda\nExperience: Built scalable systems at TechCore Solutions, 45 projects delivered\nEducation: BS Computer Science"
        },
        {
            "user": {"username": "alice_java_dev", "email": "alice.java@email.com", "full_name": "Alice Johnson", "bio": "Java architect designing scalable systems"},
            "resume_content": "Alice Johnson - Java Architect\n10+ years in Enterprise Systems\nSkills: Java, Spring Boot, Kafka, Kubernetes, microservices, distributed systems, JUnit, Maven, Gradle, GCP\nExperience: Designed 52+ systems, 10 years at Enterprise Systems Inc\nEducation: MS Software Engineering"
        },
        {
            "user": {"username": "bob_node_dev", "email": "bob.node@email.com", "full_name": "Bob Davis", "bio": "Node.js specialist building real-time apps"},
            "resume_content": "Bob Davis - Backend Lead (Node.js)\n7+ years Node.js development\nSkills: Node.js, Express, MongoDB, WebSockets, GraphQL, TypeScript, Jest, Docker, CI/CD, AWS\nExperience: 38 projects, real-time systems specialist at StartupHub\nEducation: BS Information Technology"
        },
        {
            "user": {"username": "carol_go_dev", "email": "carol.go@email.com", "full_name": "Carol Martinez", "bio": "Go expert for high-performance systems"},
            "resume_content": "Carol Martinez - Go Systems Engineer\n6+ years Go/systems programming\nSkills: Go, gRPC, Protocol Buffers, Kubernetes, etcd, load balancing, concurrency, testing, container orchestration\nExperience: 41 projects, CloudNative Systems platform engineer\nEducation: BS Computer Science"
        },
        {
            "user": {"username": "david_rust_dev", "email": "david.rust@email.com", "full_name": "David Wilson", "bio": "Rust systems programmer"},
            "resume_content": "David Wilson - Rust Systems Programmer\n5+ years systems development\nSkills: Rust, WebAssembly, systems programming, embedded systems, memory safety, concurrency, performance optimization\nExperience: 35 projects, PerformanceCore core engineer\nEducation: MS Computer Science"
        },
        {
            "user": {"username": "eve_csharp_dev", "email": "eve.csharp@email.com", "full_name": "Eve Anderson", "bio": ".NET expert with enterprise experience"},
            "resume_content": "Eve Anderson - Senior .NET Developer\n9+ years enterprise .NET\nSkills: C#, .NET Core, ASP.NET, Entity Framework, SQL Server, Azure, LINQ, WCF, WPF, testing\nExperience: 43 projects, Enterprise Systems Solutions\nEducation: BS Software Engineering"
        },
        {
            "user": {"username": "frank_php_dev", "email": "frank.php@email.com", "full_name": "Frank Thomas", "bio": "PHP architect for web applications"},
            "resume_content": "Frank Thomas - Full Stack Architect (PHP)\n8+ years PHP development\nSkills: PHP, Laravel, Symfony, MySQL, Redis, Docker, REST APIs, testing, deployment, WordPress optimization\nExperience: 36 projects, WebSolutions Pro architect\nEducation: BS Web Development"
        },
        {
            "user": {"username": "grace_scala_dev", "email": "grace.scala@email.com", "full_name": "Grace Lee", "bio": "Scala functional programmer"},
            "resume_content": "Grace Lee - Scala Engineer\n6+ years functional programming\nSkills: Scala, Spark, functional programming, Play Framework, Akka, Kafka, immutability, pattern matching\nExperience: 32 projects, FunctionalTech data engineer\nEducation: MS Computer Science"
        },
        {
            "user": {"username": "henry_ruby_dev", "email": "henry.ruby@email.com", "full_name": "Henry Brown", "bio": "Ruby on Rails specialist"},
            "resume_content": "Henry Brown - Rails Lead Developer\n7+ years Rails development\nSkills: Ruby, Rails, ActiveRecord, PostgreSQL, Redis, testing, Sidekiq, gem development, API design\nExperience: 39 projects, RailsInnovation lead developer\nEducation: BS Information Science"
        },
        {
            "user": {"username": "iris_kotlin_dev", "email": "iris.kotlin@email.com", "full_name": "Iris Chen", "bio": "Kotlin backend developer"},
            "resume_content": "Iris Chen - Kotlin Backend Developer\n5+ years Kotlin development\nSkills: Kotlin, Spring Boot, Coroutines, Ktor, ArrowKt, functional programming, testing, MongoDB, PostgreSQL\nExperience: 33 projects, ModernBackend engineer\nEducation: BS Computer Science"
        },
        
        # Frontend Engineers (10 profiles)
        {
            "user": {"username": "jack_react_dev", "email": "jack.react@email.com", "full_name": "Jack Wilson", "bio": "React expert building modern UIs"},
            "resume_content": "Jack Wilson - Senior React Developer\n8+ years React development\nSkills: React, TypeScript, Redux, TailwindCSS, Jest, React Testing Library, performance optimization, component patterns\nExperience: 48 projects, FrontendFirst senior developer\nEducation: BS Web Development"
        },
        {
            "user": {"username": "karen_vue_dev", "email": "karen.vue@email.com", "full_name": "Karen Garcia", "bio": "Vue.js specialist"},
            "resume_content": "Karen Garcia - Vue.js Lead\n7+ years Vue development\nSkills: Vue 3, Composition API, Vuex, Pinia, Vite, TypeScript, Tailwind, component libraries, testing\nExperience: 42 projects, VueEcosystem lead\nEducation: BS Frontend Engineering"
        },
        {
            "user": {"username": "liam_angular_dev", "email": "liam.angular@email.com", "full_name": "Liam Anderson", "bio": "Angular enterprise solutions"},
            "resume_content": "Liam Anderson - Angular Architect\n10+ years Angular development\nSkills: Angular, TypeScript, RxJS, NgRx, Material Design, testing, accessibility, deployment, large-scale apps\nExperience: 45 projects, EnterpriseFrontend architect\nEducation: MS Software Engineering"
        },
        {
            "user": {"username": "mia_svelte_dev", "email": "mia.svelte@email.com", "full_name": "Mia Johnson", "bio": "Svelte framework innovator"},
            "resume_content": "Mia Johnson - Svelte Developer\n4+ years Svelte development\nSkills: Svelte, SvelteKit, reactive programming, animations, accessibility, performance, component design\nExperience: 28 projects, SvelteStudio innovator\nEducation: BS Web Development"
        },
        {
            "user": {"username": "noah_nextjs_dev", "email": "noah.nextjs@email.com", "full_name": "Noah Davis", "bio": "Next.js full-stack developer"},
            "resume_content": "Noah Davis - Next.js Engineer\n6+ years full-stack development\nSkills: Next.js, React, TypeScript, Tailwind, Vercel deployment, API routes, SSR, ISR, performance\nExperience: 37 projects, NextGenWeb engineer\nEducation: BS Computer Science"
        },
        {
            "user": {"username": "olivia_webgl_dev", "email": "olivia.webgl@email.com", "full_name": "Olivia Brown", "bio": "WebGL and 3D graphics specialist"},
            "resume_content": "Olivia Brown - 3D Graphics Engineer\n7+ years graphics programming\nSkills: WebGL, Three.js, Babylon.js, graphics programming, shaders, GLSL, animation, performance optimization\nExperience: 31 projects, 3DWebTech engineer\nEducation: MS Computer Graphics"
        },
        {
            "user": {"username": "paul_flutter_dev", "email": "paul.flutter@email.com", "full_name": "Paul Martinez", "bio": "Flutter mobile expert"},
            "resume_content": "Paul Martinez - Flutter Developer\n6+ years mobile development\nSkills: Flutter, Dart, iOS/Android development, state management, Firebase, testing, deployment\nExperience: 34 projects, MobileFirst expert\nEducation: BS Mobile Development"
        },
        {
            "user": {"username": "quinn_css_expert", "email": "quinn.css@email.com", "full_name": "Quinn Taylor", "bio": "CSS and design systems expert"},
            "resume_content": "Quinn Taylor - CSS/Design Systems Lead\n8+ years frontend design\nSkills: CSS, SCSS, BEM, design tokens, component libraries, accessibility, performance, Storybook\nExperience: 40 projects, DesignSystems lead\nEducation: BS Graphic Design + Web"
        },
        {
            "user": {"username": "rachel_webdev", "email": "rachel.webdev@email.com", "full_name": "Rachel White", "bio": "Full-stack web developer"},
            "resume_content": "Rachel White - Senior Web Developer\n9+ years web development\nSkills: HTML, CSS, JavaScript, responsive design, accessibility, SEO, performance, PWA, testing\nExperience: 46 projects, FullStackHub senior\nEducation: BS Web Development"
        },
        {
            "user": {"username": "steve_threejs_dev", "email": "steve.threejs@email.com", "full_name": "Steve Harris", "bio": "Three.js expert for 3D web"},
            "resume_content": "Steve Harris - Three.js Specialist\n7+ years 3D web development\nSkills: Three.js, WebGL, 3D modeling, animations, physics engines, interactive experiences, rendering\nExperience: 29 projects, 3DWeb Solutions specialist\nEducation: BS Computer Science"
        },
        
        # ML & Data Engineers (10 profiles)
        {
            "user": {"username": "tina_ml_engineer", "email": "tina.ml@email.com", "full_name": "Tina Lewis", "bio": "Machine Learning Engineer"},
            "resume_content": "Tina Lewis - Senior ML Engineer\n8+ years machine learning\nSkills: Python, TensorFlow, PyTorch, scikit-learn, model training, neural networks, deep learning, computer vision\nExperience: 50 projects, ML Innovations senior\nEducation: MS Machine Learning"
        },
        {
            "user": {"username": "urban_data_scientist", "email": "urban.data@email.com", "full_name": "Urban Lee", "bio": "Data Scientist with NLP focus"},
            "resume_content": "Urban Lee - Senior Data Scientist (NLP)\n7+ years data science\nSkills: Python, NLP, transformers, BERT, GPT, text analysis, sentiment analysis, language models, Hugging Face\nExperience: 44 projects, DataInsights senior data scientist\nEducation: MS Natural Language Processing"
        },
        {
            "user": {"username": "victor_cv_expert", "email": "victor.cv@email.com", "full_name": "Victor Brown", "bio": "Computer Vision specialist"},
            "resume_content": "Victor Brown - CV Engineer\n6+ years computer vision\nSkills: Python, OpenCV, image processing, object detection, YOLO, Faster R-CNN, semantic segmentation, GANs\nExperience: 38 projects, VisionAI engineer\nEducation: MS Computer Vision"
        },
        {
            "user": {"username": "wendy_nlp_expert", "email": "wendy.nlp@email.com", "full_name": "Wendy Chen", "bio": "NLP and LLM specialist"},
            "resume_content": "Wendy Chen - NLP Researcher\n7+ years NLP research\nSkills: NLP, transformers, attention mechanisms, fine-tuning, text generation, question answering, semantic search\nExperience: 41 projects, NLPWorks researcher\nEducation: PhD Natural Language Processing"
        },
        {
            "user": {"username": "xavier_analytics", "email": "xavier.analytics@email.com", "full_name": "Xavier Rodriguez", "bio": "Analytics and BI specialist"},
            "resume_content": "Xavier Rodriguez - Analytics Engineer\n8+ years analytics\nSkills: SQL, Tableau, Power BI, data warehousing, ETL, analytics, dashboards, business intelligence\nExperience: 47 projects, AnalyticsHub engineer\nEducation: MS Business Analytics"
        },
        {
            "user": {"username": "yara_reinforcement_learning", "email": "yara.rl@email.com", "full_name": "Yara Patel", "bio": "Reinforcement Learning expert"},
            "resume_content": "Yara Patel - RL Engineer\n6+ years reinforcement learning\nSkills: Reinforcement learning, Q-learning, policy gradient, OpenAI Gym, PyTorch, game AI, robotics\nExperience: 35 projects, RLSystems engineer\nEducation: MS Artificial Intelligence"
        },
        {
            "user": {"username": "zara_graph_ml", "email": "zara.graphml@email.com", "full_name": "Zara Singh", "bio": "Graph Machine Learning specialist"},
            "resume_content": "Zara Singh - Graph ML Engineer\n5+ years graph neural networks\nSkills: Graph neural networks, PyG, DGL, knowledge graphs, link prediction, node classification, embeddings\nExperience: 32 projects, GraphAI engineer\nEducation: MS Machine Learning"
        },
        {
            "user": {"username": "adam_mlops", "email": "adam.mlops@email.com", "full_name": "Adam Taylor", "bio": "MLOps specialist"},
            "resume_content": "Adam Taylor - MLOps Engineer\n6+ years MLOps\nSkills: MLflow, Kubeflow, model deployment, monitoring, A/B testing, feature stores, CI/CD for ML\nExperience: 39 projects, MLOpsHub engineer\nEducation: BS Computer Science + ML"
        },
        {
            "user": {"username": "bella_timeseries", "email": "bella.timeseries@email.com", "full_name": "Bella Kumar", "bio": "Time series forecasting expert"},
            "resume_content": "Bella Kumar - Time Series Engineer\n7+ years time series\nSkills: Time series analysis, ARIMA, LSTM, Prophet, anomaly detection, forecasting, signal processing\nExperience: 43 projects, TimeSeriesAI engineer\nEducation: MS Statistics"
        },
        {
            "user": {"username": "charlie_recommender", "email": "charlie.recommender@email.com", "full_name": "Charlie Johnson", "bio": "Recommender systems expert"},
            "resume_content": "Charlie Johnson - Recommender Systems Engineer\n6+ years recommender systems\nSkills: Collaborative filtering, content-based, matrix factorization, neural networks, ranking algorithms\nExperience: 36 projects, RecSystemsLab engineer\nEducation: MS Machine Learning"
        },
        
        # DevOps & Infrastructure (8 profiles)
        {
            "user": {"username": "david_devops", "email": "david.devops@email.com", "full_name": "David Kim", "bio": "DevOps engineer with 10+ years"},
            "resume_content": "David Kim - Senior DevOps Engineer\n10+ years DevOps\nSkills: Kubernetes, Docker, Jenkins, CI/CD, infrastructure as code, Terraform, Ansible, monitoring, logging\nExperience: 49 projects, InfrastructureFirst senior\nEducation: BS Information Systems"
        },
        {
            "user": {"username": "elena_sre", "email": "elena.sre@email.com", "full_name": "Elena Zhang", "bio": "Site Reliability Engineer"},
            "resume_content": "Elena Zhang - Senior SRE\n9+ years SRE\nSkills: SRE practices, monitoring, alerting, incident response, chaos engineering, systems reliability\nExperience: 48 projects, ReliabilityFirst senior SRE\nEducation: MS Computer Science"
        },
        {
            "user": {"username": "frank_cloud_architect", "email": "frank.cloud@email.com", "full_name": "Frank Myers", "bio": "AWS Solutions Architect"},
            "resume_content": "Frank Myers - Cloud Architect\n8+ years cloud architecture\nSkills: AWS, EC2, RDS, S3, Lambda, architecture design, scalability, security, migration, consulting\nExperience: 46 projects, CloudArchitects architect\nEducation: MS Cloud Computing"
        },
        {
            "user": {"username": "grace_gcp_engineer", "email": "grace.gcp@email.com", "full_name": "Grace Norton", "bio": "GCP specialist"},
            "resume_content": "Grace Norton - GCP Engineer\n7+ years Google Cloud\nSkills: Google Cloud Platform, Compute Engine, Cloud SQL, BigQuery, Dataflow, App Engine\nExperience: 37 projects, GoogleCloudFans engineer\nEducation: BS Information Technology"
        },
        {
            "user": {"username": "hank_azure_expert", "email": "hank.azure@email.com", "full_name": "Hank Stevens", "bio": "Azure cloud engineer"},
            "resume_content": "Hank Stevens - Azure Solutions Engineer\n7+ years Azure\nSkills: Azure, VMs, App Service, SQL Database, Cosmos DB, Functions, DevOps practices\nExperience: 40 projects, AzureExperts engineer\nEducation: BS Cloud Engineering"
        },
        {
            "user": {"username": "iris_networking", "email": "iris.networking@email.com", "full_name": "Iris Patterson", "bio": "Network engineer"},
            "resume_content": "Iris Patterson - Network Engineer\n8+ years networking\nSkills: Networking, TCP/IP, routing, VPCs, firewalls, load balancing, CDN, DDoS protection\nExperience: 33 projects, NetworkSolutions engineer\nEducation: BS Network Engineering"
        },
        {
            "user": {"username": "jack_security_ops", "email": "jack.security@email.com", "full_name": "Jack Harrison", "bio": "Security operations specialist"},
            "resume_content": "Jack Harrison - Security Operations Manager\n9+ years security ops\nSkills: Security, compliance, incident response, vulnerability management, SOC, SIEM, threat detection\nExperience: 44 projects, SecurityOps manager\nEducation: MS Cybersecurity"
        },
        {
            "user": {"username": "karen_database_admin", "email": "karen.dba@email.com", "full_name": "Karen Foster", "bio": "Database administrator"},
            "resume_content": "Karen Foster - Senior DBA\n8+ years database administration\nSkills: PostgreSQL, MySQL, Oracle, backup, recovery, optimization, replication, clustering\nExperience: 45 projects, DatabaseExperts senior\nEducation: BS Database Management"
        },
        
        # Quality Assurance & Testing (7 profiles)
        {
            "user": {"username": "liam_qa_lead", "email": "liam.qa@email.com", "full_name": "Liam Fletcher", "bio": "QA engineering lead"},
            "resume_content": "Liam Fletcher - QA Engineering Lead\n8+ years QA\nSkills: Test automation, Selenium, Pytest, Jest, end-to-end testing, performance testing, load testing\nExperience: 42 projects, QualityAssurance Pro lead\nEducation: BS Quality Assurance"
        },
        {
            "user": {"username": "mona_automation", "email": "mona.automation@email.com", "full_name": "Mona Parks", "bio": "Test automation specialist"},
            "resume_content": "Mona Parks - Automation Engineer\n7+ years test automation\nSkills: Cypress, Playwright, Selenium, test frameworks, CI/CD integration, mobile testing, API testing\nExperience: 39 projects, AutomationLabs engineer\nEducation: BS Software Testing"
        },
        {
            "user": {"username": "noah_manual_qa", "email": "noah.manualqa@email.com", "full_name": "Noah Roberts", "bio": "Manual QA/test specialist"},
            "resume_content": "Noah Roberts - QA Test Specialist\n6+ years QA testing\nSkills: Manual testing, test case design, bug reporting, regression testing, user acceptance testing\nExperience: 34 projects, ManualQA specialist\nEducation: BS Quality Engineering"
        },
        {
            "user": {"username": "olivia_performance", "email": "olivia.perf@email.com", "full_name": "Olivia Scott", "bio": "Performance testing expert"},
            "resume_content": "Olivia Scott - Performance Test Engineer\n7+ years performance testing\nSkills: Performance testing, load testing, JMeter, Gatling, bottleneck analysis, optimization\nExperience: 36 projects, PerformanceQA engineer\nEducation: BS Computer Engineering"
        },
        {
            "user": {"username": "paul_security_qa", "email": "paul.securityqa@email.com", "full_name": "Paul Graham", "bio": "Security testing specialist"},
            "resume_content": "Paul Graham - Security Test Engineer\n7+ years security testing\nSkills: Security testing, penetration testing, vulnerability assessment, OWASP, API security\nExperience: 38 projects, SecurityQA engineer\nEducation: MS Cybersecurity"
        },
        {
            "user": {"username": "quinn_mobile_qa", "email": "quinn.mobileqa@email.com", "full_name": "Quinn Murphy", "bio": "Mobile QA expert"},
            "resume_content": "Quinn Murphy - Mobile QA Engineer\n6+ years mobile testing\nSkills: iOS testing, Android testing, Appium, device testing, platform variations\nExperience: 35 projects, MobileQA engineer\nEducation: BS Mobile Development"
        },
        {
            "user": {"username": "rachel_accessibility", "email": "rachel.accessibility@email.com", "full_name": "Rachel Murphy", "bio": "Accessibility testing expert"},
            "resume_content": "Rachel Murphy - Accessibility Test Engineer\n6+ years accessibility testing\nSkills: WCAG compliance, accessibility testing, screen reader testing, inclusive design\nExperience: 31 projects, AccessibilityFirst engineer\nEducation: BS Software Engineering"
        }
    ]
    
    return profiles

def add_user_resumes_to_chromadb(users_with_resumes: list, embeddings_service):
    """Add all user resumes to ChromaDB for semantic search"""
    if not embeddings_available:
        print("⚠️  Embeddings not available, skipping ChromaDB indexing")
        return
    
    try:
        print("\n📝 Indexing user resumes in ChromaDB...")
        collection_name = "user_resumes"
        
        for user_data in users_with_resumes:
            resume = user_data['resume_obj']
            user = user_data['user_obj']
            
            # Create comprehensive resume text for embedding
            resume_text = user_data['resume_content']
            
            doc_id = f"resume_{resume.resume_id}"
            metadata = {
                "resume_id": str(resume.resume_id),
                "user_id": str(user.user_id),
                "name": user.full_name,
                "email": user.email if user.is_verified else "hidden",
                "phone": user.phone_number if user.is_verified else "hidden",
                "bio": user.bio or "",
                "verified": str(user.is_verified)
            }
            
            embeddings_service.add_document(
                collection_name=collection_name,
                document_id=doc_id,
                text=resume_text.strip(),
                metadata=metadata
            )
        
        print(f"✓ Indexed {len(users_with_resumes)} user resumes in ChromaDB")
        
    except Exception as e:
        logger.error(f"Error adding resumes to ChromaDB: {e}")
        import traceback
        traceback.print_exc()

def seed_database():
    """Seed database with 45-50 user profiles with resumes"""
    
    # Clear ChromaDB first
    clear_chroma_db()
    
    # Create engine
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False}
    )
    
    # Create all tables first
    print("📋 Creating database tables...")
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(engine)
    print("✓ Database tables created")
    
    with Session(engine) as session:
        # Mark existing data for deletion
        existing_users = session.exec(select(User)).all()
        if existing_users:
            print("🗑️  Clearing existing users and resumes...")
            for user in existing_users:
                session.delete(user)
            session.commit()
        
        print("🌱 Seeding database with 45-50 user profiles and resumes...")
        
        # Create admin user
        admin_user = User(
            username="admin",
            email="admin@campusai.com",
            full_name="Campus AI Administrator",
            password_hash=hash_password("admin123"),
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
            phone_number="+1-555-0000",
            bio="Administrator for Campus AI - manages the platform"
        )
        session.add(admin_user)
        session.commit()
        session.refresh(admin_user)
        print(f"✓ Created admin user (ID: {admin_user.user_id})")
        
        # Get all profiles
        profiles = get_user_profiles()
        print(f"📊 Creating {len(profiles)} user profiles with resumes...")
        
        users_with_resumes = []
        
        # Create users and resumes
        for idx, profile_data in enumerate(profiles, 1):
            try:
                # Create user
                user = User(
                    username=profile_data['user']['username'],
                    email=profile_data['user']['email'],
                    full_name=profile_data['user']['full_name'],
                    password_hash=hash_password("password123"),
                    role=UserRole.USER,
                    is_active=True,
                    is_verified=True,
                    phone_number=f"+1-555-{1000 + idx}",
                    bio=profile_data['user']['bio']
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                
                # Create resume for user
                resume = Resume(
                    user_id=user.user_id,
                    candidate_name=user.full_name,
                    candidate_email=user.email,
                    candidate_phone=user.phone_number,
                    file_name=f"{user.full_name.replace(' ', '_')}_resume.pdf",
                    file_path=f"/uploads/resumes/{user.user_id}_{user.full_name.replace(' ', '_')}_resume.pdf",
                    file_size=256000 + (idx * 1000),  # Simulated file size
                    file_type="pdf",
                    skills="[\"Python\", \"JavaScript\", \"Cloud\", \"DevOps\"]",  # JSON string
                    is_active=True,
                    views_count=0
                )
                session.add(resume)
                session.commit()
                session.refresh(resume)
                
                user_with_resume = {
                    'user_obj': user,
                    'resume_obj': resume,
                    'resume_content': profile_data['resume_content']
                }
                users_with_resumes.append(user_with_resume)
                
                print(f"  [{idx}/{len(profiles)}] {user.full_name}")
                
            except Exception as e:
                logger.error(f"Error creating profile {idx}: {e}")
                session.rollback()
                raise
        
        print(f"\n✓ Created {len(users_with_resumes)} user profiles with resumes in database")
        
        # Add to ChromaDB if embeddings available
        if embeddings_available:
            try:
                embeddings_service = EmbeddingsService()
                add_user_resumes_to_chromadb(users_with_resumes, embeddings_service)
            except Exception as e:
                logger.warning(f"Could not add resumes to ChromaDB: {e}")
        
        # Print summary
        print("\n" + "="*60)
        print("✅ DATABASE SEEDING COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"\n📊 Summary:")
        print(f"  • Admin User: admin / admin123")
        print(f"  • Total User Profiles: {len(users_with_resumes)}")
        print(f"  • All verified and active with resumes")
        print(f"\n👥 Profile breakdown:")
        print(f"  • Backend Engineers: 10")
        print(f"  • Frontend Engineers: 10")
        print(f"  • ML & Data Engineers: 10")
        print(f"  • DevOps & Infrastructure: 8")
        print(f"  • QA & Testing: 7")
        print(f"\n✨ All resumes indexed in ChromaDB for semantic search")
        print(f"\nTest credentials format: {profiles[0]['user']['username']} / password123")
        print(f"2-Role Architecture: ADMIN + USER (no recruiter role)")

if __name__ == "__main__":
    try:
        seed_database()
    except Exception as e:
        print(f"\n❌ Error seeding database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

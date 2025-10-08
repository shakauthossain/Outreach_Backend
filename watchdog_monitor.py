import os
import time
import subprocess
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("WatchdogMonitor")

class CodeChangeHandler(FileSystemEventHandler):
    """Handler for code file changes"""
    
    def __init__(self):
        self.last_restart = 0
        self.restart_delay = 2  # seconds to wait before restart
        self.ignore_patterns = {
            '__pycache__', '.pyc', '.git', '.vscode', 
            'node_modules', '.env.local', 'logs', 
            'uploaded_csvs', 'static'
        }
        self.app_process = None
        self.celery_process = None
        
    def on_modified(self, event):
        if event.is_directory:
            return
            
        # Skip ignored patterns
        file_path = Path(event.src_path)
        if any(pattern in str(file_path) for pattern in self.ignore_patterns):
            return
            
        # Only watch Python files and important config files
        if file_path.suffix in ['.py', '.env', '.yml', '.yaml', '.json']:
            current_time = time.time()
            
            # Prevent rapid restarts
            if current_time - self.last_restart > self.restart_delay:
                logger.info(f"🔄 File changed: {file_path.name}")
                logger.info("🚀 Restarting application...")
                self.last_restart = current_time
                self.restart_application()
    
    def restart_application(self):
        """Restart the FastAPI application and related services"""
        try:
            print("🔄 Restarting services...")
            
            # In Docker environment, we restart the container
            if os.getenv('DOCKER_ENV'):
                subprocess.run(["pkill", "-f", "uvicorn"], check=False)
                subprocess.run(["pkill", "-f", "celery"], check=False)
                time.sleep(2)
                
                # Restart uvicorn
                subprocess.Popen([
                    "uvicorn", "main:app", 
                    "--host", "0.0.0.0", 
                    "--port", "8000"
                ])
                
                # Restart celery worker
                subprocess.Popen([
                    "celery", "-A", "celery_worker.celery_app", 
                    "worker", "--loglevel=info"
                ])
                
            else:
                # Local development restart
                subprocess.run(["pkill", "-f", "uvicorn"], check=False)
                time.sleep(1)
                subprocess.Popen([
                    "uvicorn", "main:app", 
                    "--host", "0.0.0.0", 
                    "--port", "8000", 
                    "--reload"
                ])
                
            logger.info("✅ Application restarted successfully")
            
        except Exception as e:
            logger.error(f"❌ Error restarting application: {e}")
    
    def start_initial_services(self):
        """Start FastAPI and Celery services initially"""
        try:
            logger.info("🌐 Starting FastAPI server...")
            self.app_process = subprocess.Popen([
                "uvicorn", "main:app", 
                "--host", "0.0.0.0", 
                "--port", "8000"
            ])
            
            logger.info("⚙️ Starting Celery worker...")  
            self.celery_process = subprocess.Popen([
                "celery", "-A", "celery_worker.celery_app", 
                "worker", "--loglevel=info"
            ])
            
            logger.info("✅ All services started successfully")
            
        except Exception as e:
            logger.error(f"❌ Error starting services: {e}")
    
    def stop_services(self):
        """Stop all running services"""
        try:
            if self.app_process:
                self.app_process.terminate()
                self.app_process.wait()
            
            if self.celery_process:
                self.celery_process.terminate()
                self.celery_process.wait()
                
            logger.info("🛑 All services stopped")
            
        except Exception as e:
            logger.error(f"❌ Error stopping services: {e}")

def start_file_watcher():
    """Start the file system watcher"""
    event_handler = CodeChangeHandler()
    observer = Observer()
    
    # Start the application initially
    logger.info("🚀 Starting initial FastAPI application...")
    event_handler.start_initial_services()
    
    # Watch current directory and subdirectories
    watch_path = os.getcwd()
    observer.schedule(event_handler, watch_path, recursive=True)
    
    logger.info(f"👁️ Watching for changes in: {watch_path}")
    logger.info("📝 Monitoring .py, .env, .yml, .yaml, .json files")
    logger.info("🔄 Auto-restart enabled for file changes")
    
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopping file watcher...")
        observer.stop()
        event_handler.stop_services()
    
    observer.join()

if __name__ == "__main__":
    start_file_watcher()
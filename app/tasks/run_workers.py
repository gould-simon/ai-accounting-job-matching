"""Script to start Celery workers."""
import subprocess
import sys
from typing import List

def start_workers():
    """Start Celery workers for different queues."""
    workers = [
        # CV Processing Worker
        [
            "celery",
            "-A", "app.tasks.celery_app",
            "worker",
            "--loglevel=INFO",
            "-Q", "cv_processing",
            "-n", "cv_worker@%h",
            "--concurrency=2"
        ],
        
        # Job Updates Worker
        [
            "celery",
            "-A", "app.tasks.celery_app",
            "worker",
            "--loglevel=INFO",
            "-Q", "job_updates",
            "-n", "job_worker@%h",
            "--concurrency=4"
        ],
        
        # Maintenance Worker
        [
            "celery",
            "-A", "app.tasks.celery_app",
            "worker",
            "--loglevel=INFO",
            "-Q", "maintenance",
            "-n", "maintenance_worker@%h",
            "--concurrency=1"
        ],
        
        # Beat Scheduler
        [
            "celery",
            "-A", "app.tasks.celery_app",
            "beat",
            "--loglevel=INFO"
        ]
    ]
    
    processes: List[subprocess.Popen] = []
    
    try:
        # Start all workers
        for worker_cmd in workers:
            process = subprocess.Popen(worker_cmd)
            processes.append(process)
        
        # Wait for any process to terminate
        while processes:
            for process in processes[:]:
                if process.poll() is not None:
                    # Process has terminated
                    if process.returncode != 0:
                        print(f"Worker failed with return code {process.returncode}")
                        # Kill all other processes
                        for p in processes:
                            if p != process and p.poll() is None:
                                p.terminate()
                        sys.exit(1)
                    processes.remove(process)
            
    except KeyboardInterrupt:
        print("\nShutting down workers...")
        for process in processes:
            process.terminate()
        
        # Wait for all processes to terminate
        for process in processes:
            process.wait()
        
        print("All workers shut down")

if __name__ == "__main__":
    start_workers()

"""Task monitoring dashboard."""
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List

from app.tasks.celery_app import celery_app
from app.core.config import settings


def get_active_tasks() -> List[Dict]:
    """Get currently running tasks.
    
    Returns:
        List of active task information
    """
    inspector = celery_app.control.inspect()
    active = inspector.active()
    
    tasks = []
    if active:
        for worker, worker_tasks in active.items():
            for task in worker_tasks:
                tasks.append({
                    "id": task["id"],
                    "name": task["name"],
                    "worker": worker,
                    "started": datetime.fromtimestamp(task["time_start"]),
                    "args": task["args"],
                    "kwargs": task["kwargs"]
                })
    
    return tasks


def get_task_stats() -> Dict:
    """Get task statistics.
    
    Returns:
        Dict containing task statistics
    """
    stats = celery_app.control.inspect().stats()
    if not stats:
        return {}
        
    total_tasks = 0
    total_workers = len(stats)
    
    for worker_stats in stats.values():
        total_tasks += sum(worker_stats.get("total", {}).values())
    
    return {
        "total_tasks": total_tasks,
        "total_workers": total_workers
    }


def get_queue_lengths() -> Dict:
    """Get number of tasks in each queue.
    
    Returns:
        Dict containing queue lengths
    """
    inspector = celery_app.control.inspect()
    reserved = inspector.reserved()
    
    queues = {
        "cv_processing": 0,
        "job_updates": 0,
        "maintenance": 0
    }
    
    if reserved:
        for worker_tasks in reserved.values():
            for task in worker_tasks:
                queue = task.get("delivery_info", {}).get("routing_key")
                if queue in queues:
                    queues[queue] += 1
    
    return queues


def render_task_monitor():
    """Render task monitoring dashboard."""
    st.title("Task Monitor")
    
    # Refresh button
    if st.button("Refresh"):
        st.experimental_rerun()
    
    # Task Stats
    st.header("Task Statistics")
    stats = get_task_stats()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Tasks Processed", stats.get("total_tasks", 0))
    with col2:
        st.metric("Active Workers", stats.get("total_workers", 0))
    
    # Queue Lengths
    st.header("Queue Lengths")
    queues = get_queue_lengths()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("CV Processing Queue", queues["cv_processing"])
    with col2:
        st.metric("Job Updates Queue", queues["job_updates"])
    with col3:
        st.metric("Maintenance Queue", queues["maintenance"])
    
    # Active Tasks
    st.header("Active Tasks")
    active_tasks = get_active_tasks()
    
    if active_tasks:
        task_df = pd.DataFrame(active_tasks)
        task_df["runtime"] = (datetime.utcnow() - task_df["started"]).dt.total_seconds()
        task_df["runtime"] = task_df["runtime"].round(2)
        
        st.dataframe(
            task_df[["id", "name", "worker", "started", "runtime"]],
            hide_index=True
        )
    else:
        st.info("No active tasks")
    
    # Task Schedule
    st.header("Task Schedule")
    schedule_data = []
    
    for task_name, task_info in celery_app.conf.beat_schedule.items():
        schedule_data.append({
            "Task": task_name,
            "Schedule": str(task_info["schedule"]),
            "Queue": celery_app.conf.task_routes.get(task_info["task"], {}).get("queue", "default")
        })
    
    if schedule_data:
        st.dataframe(
            pd.DataFrame(schedule_data),
            hide_index=True
        )
    else:
        st.info("No scheduled tasks")
    
    # Auto-refresh
    time.sleep(10)
    st.experimental_rerun()


if __name__ == "__main__":
    render_task_monitor()

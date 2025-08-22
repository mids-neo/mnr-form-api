#!/usr/bin/env python3
"""
progress_tracker.py
==================

Real-time progress tracking for medical form processing pipeline
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class ProgressStage(Enum):
    """Processing stages for progress tracking"""
    UPLOAD = "upload"
    EXTRACTION = "extraction"
    PROCESSING = "processing"
    PDF_GENERATION = "pdf_generation"
    FINALIZATION = "finalization"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ProgressUpdate:
    """Progress update data structure"""
    stage: ProgressStage
    message: str
    completed: bool = False  # Whether this stage is completed
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage.value,
            "message": self.message,
            "completed": self.completed,
            "details": self.details or {},
            "timestamp": self.timestamp
        }

class ProgressTracker:
    """Tracks processing progress and manages WebSocket connections"""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.websocket_connections: Dict[str, Any] = {}
        
    def create_session(self) -> str:
        """Create a new progress tracking session"""
        session_id = str(uuid.uuid4())
        self.active_sessions[session_id] = {
            "created_at": datetime.now().isoformat(),
            "current_stage": ProgressStage.UPLOAD,
            "updates": []
        }
        logger.info(f"📊 Created progress session: {session_id}")
        return session_id
    
    def update_progress(
        self, 
        session_id: str, 
        stage: ProgressStage, 
        message: str,
        completed: bool = False,
        details: Optional[Dict[str, Any]] = None
    ):
        """Update progress for a session"""
        if session_id not in self.active_sessions:
            logger.warning(f"Progress update for unknown session: {session_id}")
            return
            
        update = ProgressUpdate(stage, message, completed, details)
        session = self.active_sessions[session_id]
        session["current_stage"] = stage
        session["updates"].append(update)
        
        # Send to WebSocket if connected
        if session_id in self.websocket_connections:
            asyncio.create_task(
                self._send_websocket_update(session_id, update)
            )
        
        status = "✅ COMPLETED" if completed else "🔄 RUNNING"
        logger.info(f"📊 Progress [{session_id[:8]}]: {stage.value} - {status} - {message}")
    
    async def _send_websocket_update(self, session_id: str, update: ProgressUpdate):
        """Send progress update via WebSocket"""
        try:
            websocket = self.websocket_connections.get(session_id)
            if websocket:
                await websocket.send_text(json.dumps(update.to_dict()))
        except Exception as e:
            logger.error(f"Failed to send WebSocket update: {e}")
            # Remove dead connection
            if session_id in self.websocket_connections:
                del self.websocket_connections[session_id]
    
    def register_websocket(self, session_id: str, websocket):
        """Register a WebSocket connection for a session"""
        self.websocket_connections[session_id] = websocket
        logger.info(f"🔌 WebSocket connected for session: {session_id}")
    
    def unregister_websocket(self, session_id: str):
        """Unregister a WebSocket connection"""
        if session_id in self.websocket_connections:
            del self.websocket_connections[session_id]
            logger.info(f"🔌 WebSocket disconnected for session: {session_id}")
    
    def get_session_progress(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current progress for a session"""
        return self.active_sessions.get(session_id)
    
    def cleanup_session(self, session_id: str):
        """Clean up a completed session"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        if session_id in self.websocket_connections:
            del self.websocket_connections[session_id]
        logger.info(f"🧹 Cleaned up session: {session_id}")

# Global progress tracker instance
progress_tracker = ProgressTracker()

class ProgressCallback:
    """Callback wrapper for pipeline progress updates"""
    
    def __init__(self, session_id: str, tracker: ProgressTracker):
        self.session_id = session_id
        self.tracker = tracker
        
    def on_extraction_start(self, method: str):
        self.tracker.update_progress(
            self.session_id,
            ProgressStage.EXTRACTION,
            f"Starting data extraction using {method}",
            completed=False,
            details={"method": method}
        )
    
    def on_extraction_progress(self, progress: float, message: str):
        self.tracker.update_progress(
            self.session_id,
            ProgressStage.EXTRACTION,
            message,
            completed=False
        )
    
    def on_extraction_complete(self, fields_extracted: int, cost: float = 0.0, time_taken: float = 0.0):
        self.tracker.update_progress(
            self.session_id,
            ProgressStage.EXTRACTION,
            f"Data extraction completed - {fields_extracted} fields extracted",
            completed=True,
            details={
                "fields_extracted": fields_extracted,
                "cost": cost,
                "time_taken": time_taken
            }
        )
    
    def on_processing_start(self, output_format: str):
        self.tracker.update_progress(
            self.session_id,
            ProgressStage.PROCESSING,
            f"Processing data for {output_format.upper()} format",
            completed=False,
            details={"output_format": output_format}
        )
    
    def on_processing_complete(self):
        self.tracker.update_progress(
            self.session_id,
            ProgressStage.PROCESSING,
            "Data processing completed",
            completed=True
        )
    
    def on_pdf_generation_start(self, output_format: str):
        self.tracker.update_progress(
            self.session_id,
            ProgressStage.PDF_GENERATION,
            f"Generating {output_format.upper()} PDF",
            completed=False,
            details={"output_format": output_format}
        )
    
    def on_pdf_generation_progress(self, progress: float, message: str):
        self.tracker.update_progress(
            self.session_id,
            ProgressStage.PDF_GENERATION,
            message,
            completed=False
        )
    
    def on_pdf_generation_complete(self, fields_filled: int, output_path: str):
        self.tracker.update_progress(
            self.session_id,
            ProgressStage.PDF_GENERATION,
            f"PDF generation completed - {fields_filled} fields filled",
            completed=True,
            details={
                "fields_filled": fields_filled,
                "output_path": output_path
            }
        )
    
    def on_finalization_start(self):
        """Called when starting final processing steps after PDF generation"""
        self.tracker.update_progress(
            self.session_id,
            ProgressStage.FINALIZATION,
            "Finalizing PDF and preparing response",
            completed=False
        )
    
    def on_finalization_progress(self, progress: float, message: str):
        """Called during finalization steps"""
        self.tracker.update_progress(
            self.session_id,
            ProgressStage.FINALIZATION,
            message,
            completed=False
        )
    
    def on_finalization_complete(self):
        """Called when finalization is done"""
        self.tracker.update_progress(
            self.session_id,
            ProgressStage.FINALIZATION,
            "Finalization completed",
            completed=True
        )
    
    def on_pipeline_complete(self, result: Dict[str, Any]):
        self.tracker.update_progress(
            self.session_id,
            ProgressStage.COMPLETED,
            "Processing completed successfully",
            completed=True,
            details=result
        )
    
    def on_pipeline_error(self, error: str, stage: str):
        error_stage_map = {
            "extraction": ProgressStage.EXTRACTION,
            "processing": ProgressStage.PROCESSING,
            "pdf_generation": ProgressStage.PDF_GENERATION,
        }
        stage_enum = error_stage_map.get(stage, ProgressStage.FAILED)
        
        self.tracker.update_progress(
            self.session_id,
            ProgressStage.FAILED,
            0.0,
            f"Processing failed at {stage}: {error}",
            {"error": error, "failed_stage": stage}
        )
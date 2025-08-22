#!/usr/bin/env python3
"""
Optimized Medical Form Processor
Implements caching, parallel processing, and smart PDF method selection
"""

import os
import logging
import hashlib
import asyncio
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

class OptimizedFormProcessor:
    """Optimized form processor with caching and parallel processing"""
    
    def __init__(self):
        self.extraction_cache = {}
        self.pdf_method_cache = {}
        self.template_cache = {}
        self.cache_ttl = timedelta(minutes=30)
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    def get_file_hash(self, file_content: bytes) -> str:
        """Generate hash of file content for caching"""
        return hashlib.sha256(file_content).hexdigest()
    
    def get_cached_extraction(self, file_hash: str, method: str) -> Optional[Dict]:
        """Get cached extraction if available and not expired"""
        cache_key = f"{file_hash}_{method}"
        if cache_key in self.extraction_cache:
            result, timestamp = self.extraction_cache[cache_key]
            if datetime.now() - timestamp < self.cache_ttl:
                logger.info(f"✅ Cache hit for extraction: {cache_key[:16]}...")
                return result
            else:
                # Remove expired cache
                del self.extraction_cache[cache_key]
        return None
    
    def cache_extraction(self, file_hash: str, method: str, result: Dict):
        """Cache extraction result"""
        cache_key = f"{file_hash}_{method}"
        self.extraction_cache[cache_key] = (result, datetime.now())
        logger.info(f"💾 Cached extraction: {cache_key[:16]}...")
        
        # Clean old cache entries
        self._cleanup_cache()
    
    def _cleanup_cache(self):
        """Remove expired cache entries"""
        now = datetime.now()
        expired_keys = []
        
        for key, (_, timestamp) in self.extraction_cache.items():
            if now - timestamp > self.cache_ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.extraction_cache[key]
            logger.debug(f"🗑️ Removed expired cache: {key[:16]}...")
    
    async def process_with_cache(self, file_content: bytes, method: str, 
                                 output_format: str, config: Dict) -> Dict:
        """Process form with caching and optimization"""
        
        # Check extraction cache
        file_hash = self.get_file_hash(file_content)
        cached_extraction = self.get_cached_extraction(file_hash, method)
        
        if cached_extraction:
            # Use cached extraction, skip to PDF generation
            logger.info("⚡ Using cached extraction, skipping OCR/AI processing")
            return await self._generate_pdf_only(cached_extraction, output_format, config)
        
        # If not cached, process normally but cache the result
        return await self._process_and_cache(file_content, file_hash, method, output_format, config)
    
    async def _process_and_cache(self, file_content: bytes, file_hash: str, 
                                 method: str, output_format: str, config: Dict) -> Dict:
        """Process form and cache extraction results"""
        
        # Save to temp file for processing
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(file_content)
            temp_path = tmp.name
        
        try:
            # Import pipeline components
            from pipeline import process_medical_form
            
            # Process the form
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                process_medical_form,
                temp_path,
                output_format,
                method,
                config
            )
            
            # Cache the extraction result if successful
            if result and hasattr(result, 'extraction_result') and result.extraction_result:
                self.cache_extraction(file_hash, method, result.extraction_result.data)
            
            return result
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    async def _generate_pdf_only(self, extraction_data: Dict, output_format: str, config: Dict) -> Dict:
        """Generate PDF from cached extraction data"""
        
        # Import pipeline components
        from pipeline import PipelineConfig, PipelineResult
        from pipeline.json_processor import JSONProcessorOrchestrator
        from pipeline.mnr_pdf_filler import MNRPDFFiller
        from pipeline.ash_pdf_filler import ASHPDFFiller
        
        # Process JSON
        json_processor = JSONProcessorOrchestrator()
        processing_result = json_processor.full_pipeline(
            raw_data=extraction_data,
            output_format=output_format
        )
        
        # Generate PDF based on format
        if output_format.lower() == "ash":
            filler = ASHPDFFiller()
        else:
            filler = MNRPDFFiller()
        
        # Find template
        template_dir = Path(__file__).parent / "templates"
        template_name = "ash_medical_form.pdf" if output_format.lower() == "ash" else "mnr_form.pdf"
        template_path = template_dir / template_name
        
        # Generate output path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(config.get('output_directory', 'outputs'))
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"cached_{output_format}_{timestamp}.pdf"
        
        # Fill PDF
        filling_result = await asyncio.get_event_loop().run_in_executor(
            self.executor,
            filler.fill_pdf,
            processing_result.data,
            str(template_path),
            str(output_path)
        )
        
        # Create pipeline result
        return PipelineResult(
            success=filling_result.success,
            stage_reached="completed",
            extraction_result=type('ExtResult', (), {
                'data': extraction_data, 
                'method': 'cached',
                'method_used': 'cached',
                'success': True
            })(),
            processing_result=processing_result,
            filling_result=filling_result,
            output_pdf=str(output_path) if filling_result.success else None,
            fields_extracted=len(extraction_data),
            fields_filled=filling_result.fields_filled,
            total_processing_time=0.5,  # Very fast since cached
            config=PipelineConfig(**config)
        )
    
    async def process_both_parallel(self, file_content: bytes, method: str, config: Dict, progress_callback=None) -> Tuple[Any, Any]:
        """Process both MNR and ASH forms in parallel with shared extraction"""
        
        # Get file hash for caching
        file_hash = self.get_file_hash(file_content)
        
        # Check if extraction is cached
        cached_extraction = self.get_cached_extraction(file_hash, method)
        
        if cached_extraction:
            # Generate both PDFs in parallel from cached extraction
            logger.info("⚡ Using cached extraction for parallel PDF generation")
            
            # Update progress for cached extraction
            if progress_callback:
                progress_callback.on_extraction_complete(
                    len(cached_extraction),
                    "cached"
                )
                progress_callback.on_processing_start()
            
            mnr_task = self._generate_pdf_only(cached_extraction, "mnr", config)
            ash_task = self._generate_pdf_only(cached_extraction, "ash", config)
            
            mnr_result, ash_result = await asyncio.gather(mnr_task, ash_task)
            
            # Update progress for completion
            if progress_callback:
                progress_callback.on_processing_complete()
            
            return mnr_result, ash_result
        
        # If not cached, extract once and generate both PDFs in parallel
        logger.info("🔄 Extracting once, generating both PDFs in parallel")
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(file_content)
            temp_path = tmp.name
        
        try:
            # Import and run extraction
            from pipeline.ocr_extraction import ExtractionOrchestrator
            
            extractor = ExtractionOrchestrator()
            extraction_result = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                extractor.extract,
                temp_path,
                method,
                True  # fallback
            )
            
            if extraction_result and extraction_result.success:
                # Update progress for completed extraction
                if progress_callback:
                    progress_callback.on_extraction_complete(
                        len(extraction_result.data),
                        extraction_result.method_used if hasattr(extraction_result, 'method_used') else method
                    )
                    progress_callback.on_processing_start()
                
                # Cache the extraction
                self.cache_extraction(file_hash, method, extraction_result.data)
                
                # Generate both PDFs in parallel
                mnr_task = self._generate_pdf_only(extraction_result.data, "mnr", config)
                ash_task = self._generate_pdf_only(extraction_result.data, "ash", config)
                
                mnr_result, ash_result = await asyncio.gather(mnr_task, ash_task)
                
                # Update progress for completion
                if progress_callback:
                    progress_callback.on_processing_complete()
                
                return mnr_result, ash_result
            else:
                raise Exception("Extraction failed")
                
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

# Global instance
optimized_processor = OptimizedFormProcessor()

async def process_optimized(file_content: bytes, method: str, output_format: str, config: Dict, progress_callback=None) -> Any:
    """Main entry point for optimized processing"""
    
    if output_format.lower() == "both":
        # Process both in parallel with shared extraction
        mnr_result, ash_result = await optimized_processor.process_both_parallel(
            file_content, method, config, progress_callback
        )
        
        # Combine results
        result = mnr_result  # Use MNR as primary
        if hasattr(ash_result, 'output_pdf'):
            result.ash_pdf = ash_result.output_pdf
            result.ash_filename = os.path.basename(ash_result.output_pdf) if ash_result.output_pdf else None
        if hasattr(mnr_result, 'output_pdf'):
            result.mnr_filename = os.path.basename(mnr_result.output_pdf) if mnr_result.output_pdf else None
        
        return result
    else:
        # Single format processing with cache
        return await optimized_processor.process_with_cache(
            file_content, method, output_format, config
        )
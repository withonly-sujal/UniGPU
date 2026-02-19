"""
UniGPU Agent — Artifact Uploader
Zips job output and uploads it to the backend via HTTP.
"""

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger("unigpu.agent.uploader")


class ArtifactUploader:
    """
    Uploads job output artifacts (model weights, logs, etc.) to the backend.
    """

    def __init__(self, backend_http_url: str, agent_token: str):
        self.backend_http_url = backend_http_url.rstrip("/")
        self.agent_token = agent_token

    async def upload(self, job_id: str, output_dir: str) -> bool:
        """
        Zip the output directory and upload to the backend.

        Args:
            job_id: The job identifier.
            output_dir: Path to the output directory to archive.

        Returns:
            True if upload succeeded, False otherwise.
        """
        output_path = Path(output_dir)

        if not output_path.exists() or not any(output_path.iterdir()):
            logger.info("No output artifacts for job %s — skipping upload", job_id)
            return True  # Not an error

        archive_path: Optional[str] = None

        try:
            # Create a zip archive of the output directory
            archive_path = await self._create_archive(job_id, output_path)
            if not archive_path:
                return False

            # Upload to backend
            return await self._upload_file(job_id, archive_path)

        except Exception as exc:
            logger.exception("Artifact upload failed for job %s: %s", job_id, exc)
            return False

        finally:
            # Clean up temp archive
            if archive_path and Path(archive_path).exists():
                try:
                    Path(archive_path).unlink()
                except Exception:
                    pass

    async def _create_archive(self, job_id: str, output_path: Path) -> Optional[str]:
        """Create a zip archive of the output directory."""
        try:
            temp_dir = tempfile.mkdtemp()
            archive_base = Path(temp_dir) / f"output-{job_id}"
            archive_path = shutil.make_archive(
                str(archive_base),
                "zip",
                root_dir=str(output_path.parent),
                base_dir=output_path.name,
            )
            size_mb = Path(archive_path).stat().st_size / (1024 * 1024)
            logger.info(
                "Created archive for job %s: %.1f MB", job_id, size_mb
            )
            return archive_path
        except Exception as exc:
            logger.error("Failed to create archive for job %s: %s", job_id, exc)
            return None

    async def _upload_file(self, job_id: str, archive_path: str) -> bool:
        """Upload the archive to the backend endpoint."""
        url = f"{self.backend_http_url}/api/jobs/{job_id}/artifacts"
        headers = {"Authorization": f"Bearer {self.agent_token}"}

        async with httpx.AsyncClient(timeout=300) as client:
            with open(archive_path, "rb") as f:
                files = {"file": (f"output-{job_id}.zip", f, "application/zip")}
                resp = await client.post(url, headers=headers, files=files)

            if resp.status_code in (200, 201):
                logger.info("Artifacts uploaded for job %s", job_id)
                return True
            else:
                logger.error(
                    "Upload failed for job %s: HTTP %d — %s",
                    job_id, resp.status_code, resp.text[:300],
                )
                return False

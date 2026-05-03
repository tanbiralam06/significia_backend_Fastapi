import os
import uuid
import tempfile
import httpx
from typing import Optional
from sqlalchemy.orm import Session

async def resolve_logo_to_local_path(db_path: Optional[str], db: Session) -> Optional[str]:
    """
    Resolves a database path (local, cloud key, or URL) to a local filesystem path.
    Downloads cloud/remote files to temporary storage if necessary.
    """
    with open("debug_logo.log", "a") as f:
        f.write(f"\nDEBUG: resolve_logo_to_local_path called with db_path: {db_path}\n")
    if not db_path:
        with open("debug_logo.log", "a") as f:
            f.write("DEBUG: db_path is empty/None\n")
        return None

    # 1. Full URL (e.g. from a cloud provider or external link)
    if db_path.startswith(("http://", "https://")):
        # Standardize 0.0.0.0 to 127.0.0.1 for local dev immediately
        if "0.0.0.0" in db_path:
            db_path = db_path.replace("0.0.0.0", "127.0.0.1")

        urls_to_try = [db_path]
        
        # If the URL looks like a public IP/domain (not localhost), add an internal fallback
        if "127.0.0.1" not in db_path and "localhost" not in db_path:
            from urllib.parse import urlparse
            parsed = urlparse(db_path)
            # Create a localhost version of the same URL (keeping the port)
            fallback_netloc = f"127.0.0.1:{parsed.port}" if parsed.port else "127.0.0.1"
            fallback_url = parsed._replace(netloc=fallback_netloc).geturl()
            urls_to_try.append(fallback_url)

        for url in urls_to_try:
            try:
                with open("debug_logo.log", "a") as f:
                    f.write(f"DEBUG: Attempting to download from URL: {url}\n")
                
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        ext = os.path.splitext(url.split('?')[0])[1] or '.png'
                        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                        tmp.write(resp.content)
                        tmp.close()
                        with open("debug_logo.log", "a") as f:
                            f.write(f"DEBUG: Successfully downloaded to: {tmp.name}\n")
                        return tmp.name
                    else:
                        with open("debug_logo.log", "a") as f:
                            f.write(f"DEBUG: Download failed from {url} with status {resp.status_code}\n")
            except Exception as e:
                with open("debug_logo.log", "a") as f:
                    f.write(f"DEBUG: Connection failed for {url}: {e}\n")
                continue # Try next URL in list (the fallback)

        return None

    # 2. Local Storage Path
    else:
        with open("debug_logo.log", "a") as f:
            f.write(f"DEBUG: Local path detected: {db_path}\n")
        # Try relative to CWD first (server root)
        abs_path = os.path.abspath(db_path)
        with open("debug_logo.log", "a") as f:
            f.write(f"DEBUG: Checking abspath: {abs_path}\n")
        if os.path.exists(abs_path):
            with open("debug_logo.log", "a") as f:
                f.write("DEBUG: Found at abspath\n")
            return abs_path
        
        # Try relative to backend root specifically if called from a submodule
        file_dir = os.path.dirname(os.path.abspath(__file__))
        backend_root = os.path.abspath(os.path.join(file_dir, '..', '..'))
        joined_path = os.path.join(backend_root, db_path)
        with open("debug_logo.log", "a") as f:
            f.write(f"DEBUG: Checking joined path: {joined_path}\n")
        if os.path.exists(joined_path):
            with open("debug_logo.log", "a") as f:
                f.write("DEBUG: Found at joined path\n")
            return joined_path

    with open("debug_logo.log", "a") as f:
        f.write("DEBUG: NO PATH RESOLVED\n")
    return None

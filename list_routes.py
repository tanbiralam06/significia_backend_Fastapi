
import sys
import os

# Set up path to include the app directory
sys.path.append(os.getcwd())

try:
    from app.main import app
    print("Successfully imported app.main")
except Exception as e:
    print(f"Error importing app.main: {e}")
    sys.exit(1)

print("\n--- Registered Routes ---")
for route in app.routes:
    if hasattr(route, 'path'):
        # Filter for our new route
        if "data-rectification" in route.path:
             print(f"[FOUND] {route.path} (Methods: {route.methods})")
        else:
             # Just showing some other routes for context
             if "/api/v1/" in route.path and any(x in route.path for x in ["auth", "client", "master"]):
                 print(f" (context) {route.path}")

print("--- End of Routes ---\n")

try:
    from app.api.v1 import rectification_routes
    print("Successfully imported rectification_routes module")
    print(f"Router defined: {hasattr(rectification_routes, 'router')}")
except Exception as e:
    print(f"Error importing rectification_routes: {e}")

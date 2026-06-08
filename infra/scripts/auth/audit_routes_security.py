import sys
import os

# Add root directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from fastapi.routing import APIRoute
from app_skeleton.api.main import app

def generate_audit():
    with open("docs/25_SECURITY_ROUTE_AUDIT.md", "w") as f:
        f.write("# Security Route Audit\n\n")
        
        public_routes = []
        protected_routes = []
        admin_routes = []
        unprotected_api_routes = []
        
        for route in app.routes:
            if isinstance(route, APIRoute):
                # Inspect dependencies
                deps = [d.dependency.__name__ for d in route.dependencies if hasattr(d.dependency, '__name__')]
                
                # Check for global dependencies on the app
                global_deps = []
                # It's hard to dynamically extract router dependencies applied via include_router
                # unless we check the route's dependencies list which FastAPI flattens.
                all_deps = deps
                
                route_info = f"- **{route.methods}** `{route.path}` (Function: `{route.endpoint.__name__}`)"
                
                if "require_platform_user" in all_deps or "require_firebase_user" in all_deps or "require_admin_user" in all_deps:
                    if "require_admin_user" in all_deps:
                        admin_routes.append(route_info)
                    else:
                        protected_routes.append(route_info)
                elif route.path.startswith("/api/") and route.path not in ["/api/auth/register-request"]:
                    # Health/status and public endpoints are ok to be public, but all other /api/ should be protected
                    if "health" in route.path.lower() or "public" in route.path.lower() or route.path == "/api/admin/allowed-emails":
                        public_routes.append(route_info)
                    else:
                        unprotected_api_routes.append(route_info)
                else:
                    public_routes.append(route_info)
                    
        f.write("## Unprotected API Routes (ACTION REQUIRED)\n")
        if not unprotected_api_routes:
            f.write("None found. Excellent.\n\n")
        else:
            for r in unprotected_api_routes:
                f.write(r + "\n")
            f.write("\n")
            
        f.write("## Admin Only Routes\n")
        for r in admin_routes:
            f.write(r + "\n")
        f.write("\n")
        
        f.write("## Protected API Routes\n")
        for r in protected_routes:
            f.write(r + "\n")
        f.write("\n")
        
        f.write("## Public Routes\n")
        for r in public_routes:
            f.write(r + "\n")
        f.write("\n")

if __name__ == "__main__":
    generate_audit()
    print("Audit written to docs/25_SECURITY_ROUTE_AUDIT.md")

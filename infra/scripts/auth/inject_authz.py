import os
import re

TARGET_FILES = [
    "omeia/api/routers/datapad.py",
    "omeia/api/routers/digitalization.py",
    "omeia/api/routers/copilot.py",
    "omeia/api/routers/knowledge.py",
    "omeia/api/routers/storage.py",
    "omeia/api/routers/vault.py",
    "omeia/api/routers/research.py"
]

def inject_authz():
    for filepath in TARGET_FILES:
        if not os.path.exists(filepath):
            continue
            
        with open(filepath, "r") as f:
            content = f.read()
            
        # Add imports if missing
        if "from app_skeleton.security.permissions import require_role" not in content:
            # find first import
            content = re.sub(r'^(import|from)', r'from app_skeleton.security.permissions import require_role\nfrom app_skeleton.security.auth import require_platform_user\n\1', content, count=1)
            
        # Find all defs under @router.(post|put|patch|delete)
        pattern = r'(@router\.(?:post|put|patch|delete)\(.*?\)\s+def\s+\w+\()([^)]*)(\)\s*(?:->\s*[^:]+)?:)'
        
        def replacer(match):
            decorator_and_def = match.group(1)
            params = match.group(2)
            ret_and_colon = match.group(3)
            
            # If Depends(require_platform_user) is already in params, we might just need to ensure require_role is there.
            if "user: dict" not in params and "user:" not in params:
                if params.strip():
                    new_params = params + ", user: dict = Depends(require_platform_user)"
                else:
                    new_params = "user: dict = Depends(require_platform_user)"
            else:
                new_params = params
                
            return decorator_and_def + new_params + ret_and_colon + '\n    require_role(user, ["editor", "admin"])'
            
        new_content = re.sub(pattern, replacer, content, flags=re.DOTALL)
        
        # Some endpoints might have Depends(require_firebase_user). Let's replace it.
        new_content = new_content.replace("require_firebase_user", "require_platform_user")
        
        with open(filepath, "w") as f:
            f.write(new_content)

if __name__ == "__main__":
    inject_authz()
    print("Injected authorization checks.")

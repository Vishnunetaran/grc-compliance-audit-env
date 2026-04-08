import uvicorn
from grc_compliance_audit_env.server.app import app

def main():
    """Entry point for the [project.scripts] 'server' command."""
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860, log_level="info")

if __name__ == "__main__":
    main()

import asyncio
import logging
import shutil
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration & Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom Exceptions (Clean Error Handling)
# ---------------------------------------------------------------------------
class OSINTError(Exception):
    """Base exception for all OSINT tool-related errors."""
    pass

class ToolNotFoundError(OSINTError):
    """Raised when the required external binary is missing."""
    pass

class ToolExecutionError(OSINTError):
    """Raised when the external tool fails (non-zero exit code)."""
    pass

class ToolTimeoutError(OSINTError):
    """Raised when the execution exceeds the allowed time limit."""
    pass

# ---------------------------------------------------------------------------
# Internal Core Logic (Private functions)
# ---------------------------------------------------------------------------
async def _execute_holehe(email: str, timeout: int) -> str:
    """
    Handles the asynchronous execution of the 'holehe' binary.
    
    Args:
        email: The target email address.
        timeout: Maximum execution time in seconds.
        
    Raises:
        ToolNotFoundError: If the binary is not in the system PATH.
        ToolExecutionError: If the process returns an error.
        ToolTimeoutError: If the process hangs.
        
    Returns:
        The raw stdout string from the command.
    """
    # Fail Fast: Check if tool exists before spinning up async processes
    if not shutil.which("holehe"):
        raise ToolNotFoundError("The 'holehe' binary is not installed or not in PATH.")

    command = ["holehe", email, "--only-used"]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), 
            timeout=timeout
        )
        
        if process.returncode != 0:
            error_msg = stderr.decode('utf-8').strip()
            raise ToolExecutionError(f"Process failed (Code {process.returncode}): {error_msg}")
            
        return stdout.decode('utf-8').strip()
        
    except asyncio.TimeoutError:
        # Prevent zombie processes
        try:
            process.kill()
        except ProcessLookupError:
            pass 
        raise ToolTimeoutError(f"Scan timed out after {timeout} seconds.")

def _parse_output(raw_output: str, email: str) -> str:
    """
    Parses and formats the raw tool output into a clean LLM-friendly string.
    """
    if not raw_output:
        return f"Scan completed natively, but no registered accounts were found for {email}."
    
    # Here you could add regex to strip ANSI colors or extract specific JSON data
    # For now, we wrap the raw output nicely for the LLM
    return f"OSINT Results for '{email}':\n\n{raw_output}"

# ---------------------------------------------------------------------------
# Public API (Exposed to MCP Server)
# ---------------------------------------------------------------------------
async def run_email_osint(email: str, timeout_seconds: int = 60) -> str:
    """
    Executes an OSINT scan on a specific email address.
    This is the main entry point to be wrapped by the MCP server.
    
    Args:
        email (str): The target email address to investigate.
        timeout_seconds (int): Max execution time. Defaults to 60.
        
    Returns:
        str: The formatted results or a safe, descriptive error message.
    """
    logger.info(f"Initiating email OSINT workflow for: {email}")
    
    try:
        # 1. Execute
        raw_data = await _execute_holehe(email, timeout_seconds)
        
        # 2. Parse & Format
        formatted_result = _parse_output(raw_data, email)
        
        logger.info(f"Successfully completed scan for: {email}")
        return formatted_result
        
    except OSINTError as base_err:
        # Handled custom exceptions (expected failures)
        logger.warning(f"OSINT scan failed gracefully: {str(base_err)}")
        return f"Error executing scan: {str(base_err)}"
        
    except Exception as unexpected_err:
        # Unhandled exceptions (system crashes, memory errors)
        logger.exception("A critical unexpected error occurred.")
        return f"Critical system error during OSINT scan: {str(unexpected_err)}"

# ---------------------------------------------------------------------------
# Standalone Testing Block
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    async def run_test():
        test_target = "test@example.com"
        print(f"[*] Starting local test for {test_target}...\n")
        
        result = await run_email_osint(test_target, timeout_seconds=120)
        
        print("\n[RESULT]")
        print(result)
        
    asyncio.run(run_test())
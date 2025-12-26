"""
Script to clear demo data safely and check upload functionality
"""

CLEAR_KEYS = [
    'jr_research_bookmarks',      # Research bookmarks
    'jr_research_history',        # Search history
    'jr_drafting_state_v1',       # Drafting studio state
    'jr_activeCase',              # Active case
    'junior:canvasToolbarPos',    # Canvas toolbar position
    'junior:radialPos',           # Radial menu position
]

# Chat messages use dynamic keys based on case
# Format: 'jr_chat_messages_<case_id>'

print("🧹 CLEAR DEMO DATA UTILITY")
print("=" * 60)
print()
print("This script will clear the following data from localStorage:")
print()
for key in CLEAR_KEYS:
    print(f"  ✓ {key}")
print()
print("  ✓ All chat message histories (jr_chat_messages_*)")
print()
print("⚠️  This will NOT affect:")
print("  - Backend data")
print("  - Uploaded files on server")
print("  - Database records")
print("  - Configuration settings")
print()
print("=" * 60)
print()
print("To clear data, add this to browser console:")
print()
print("JavaScript code to run in browser console:")
print("-" * 60)
print("""
// Clear all Junior-related localStorage
const keys = [
  'jr_research_bookmarks',
  'jr_research_history', 
  'jr_drafting_state_v1',
  'jr_activeCase',
  'junior:canvasToolbarPos',
  'junior:radialPos'
];

keys.forEach(key => localStorage.removeItem(key));

// Clear all chat messages
Object.keys(localStorage)
  .filter(key => key.startsWith('jr_chat_messages_'))
  .forEach(key => localStorage.removeItem(key));

console.log('✅ Demo data cleared!');
console.log('🔄 Refresh the page to see clean state');
""")
print("-" * 60)
print()
print("📋 UPLOAD FUNCTIONALITY CHECK")
print("=" * 60)
print()
print("Checking upload endpoint availability...")
print()

import httpx
import asyncio

async def check_upload():
    try:
        # Check if upload endpoint exists
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Try to access API docs to see if upload is available
            resp = await client.get("http://localhost:8000/docs")
            if resp.status_code == 200:
                print("✅ Backend is running")
                
                # Check if python-multipart is installed
                try:
                    import multipart
                    print("✅ python-multipart is installed")
                    print("✅ Upload endpoint should be available at:")
                    print("   POST /api/v1/documents/upload")
                    print()
                    print("📤 Upload Test:")
                    print("   - Navigate to Detective Wall")
                    print("   - Click the Upload button (top toolbar)")
                    print("   - Select PDF, DOCX, or text files")
                    print("   - Files will appear as Evidence nodes")
                    print()
                except ImportError:
                    print("❌ python-multipart is NOT installed")
                    print("🔧 To fix, run: pip install python-multipart")
                    print()
            else:
                print("❌ Backend not responding")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure backend is running: python start.py")

if __name__ == "__main__":
    asyncio.run(check_upload())

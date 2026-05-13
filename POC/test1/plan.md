# POC: test1 - Discord Bot + LM Studio Integration

## Approach
First implementation attempt of the Discord bot with LM Studio integration, following the architecture defined in app_plan.md.

**Initial approach**: tkinter desktop GUI
**Current approach**: Flask web-based GUI (switched due to tkinter unavailability on Python 3.13/Fedora)

## Key Decisions
- Using tkinter for GUI (built-in, no extra dependency) → **Changed to Flask** (tkinter not available on Python 3.13/Fedora)
- Async discord.py for bot event loop
- Threading for GUI updates from async bot
- JSON configuration file
- Modular discord bot architecture (6 focused modules under `src/discord_bot/`)
- Safe image download with hostname whitelist (cdn.discordapp.com, media.discordapp.net)
- Isolated mini-context for image description to prevent context overflow

## Testing Steps
1. Test Discord connection ✅
2. Test LM Studio connection ✅
3. Test tool calling ✅
4. Test GUI responsiveness ✅
5. Test image describe with isolated context ✅ (5/13/2026)
6. Test discord.py 2.x is_image() compatibility ✅ (5/13/2026)

## Results
### Verified Working (5/13/2026)
- Flask server starts on port 5000
- Discord bot connects and responds to mentions
- LM Studio integration for AI-powered responses
- Session-based conversation context per channel
- LM Studio tool calling (end_session, image_describe)
- Message queuing during processing
- Configurable settings (temperature, max_tokens, delay, system prompt)
- Debug panel at /debug route
- Token metrics streaming display
- Safe image download with hostname whitelist
- **BUG-002 all fixes verified**:
  - System prompt guides intent-based image tool usage
  - User-friendly blocked hostname error messages
  - Isolated mini-context prevents context overflow (1160 tokens vs 6917)
  - discord.py 2.x is_image() compatibility (no warnings)

## Lessons Learned
1. tkinter is not bundled with Python 3.13 on Fedora/Nobara → Flask is more portable
2. discord.py 2.x: `is_image` is a property, not a method → use hasattr() guard
3. Image base64 data in conversation history causes context overflow → use isolated mini-context
4. LM Studio needs explicit guidance to distinguish casual image messages from description requests
5. Raw security errors should never be sent to LM Studio → use user-friendly messages
6. Modular architecture (6 files vs 1 large file) is much easier to maintain and debug
7. POC-first approach works well - each POC folder is independently testable

## Next Feature: Server Configuration System (FEAT-001)
- Per-server enable/disable and per-channel allow/deny lists
- Web UI "Server Config" tab
- Bot checks server/channel access before processing messages

## CSS Refactoring (2026-01-13)
- **Decision**: Aggressively minimized CSS from 1,658 lines to ~200 lines
- **Rationale**: During active development, overly styled CSS wastes AI tokens and effort. The page is an internal admin tool, not a public-facing website. Functional > beautiful at this stage.
- **Removed**: Custom scrollbars, animations, hover effects, transitions, collapsible panels, resize handles, decorative elements, responsive design rules
- **Approach**: Single `minimal.css` file with essential layout and styling only
- **Future**: Aesthetics can be improved later once functionality is stable. The current approach saves development time and tokens.
- **Files changed**:
  - Removed: `src/static/styles.css` (1,221 lines)
  - Removed: `src/static/debug_styles.css` (437 lines)
  - Added: `src/static/minimal.css` (~200 lines)
  - Updated: `src/templates/index.html` → links to `minimal.css`
  - Updated: `src/templates/debug.html` → links to `minimal.css`

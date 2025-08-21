# Media Path Configuration

The Gartan Scraper Bot now supports configurable media paths for all persistent files.

## Configuration

Set the `MEDIA` environment variable to specify where all persistent files should be stored:

```bash
export MEDIA=/path/to/your/media/directory
```

## Files Affected

All persistent files are now stored relative to the media directory:

- **Database**: `${MEDIA}/gartan_availability.db`
- **Cache**: `${MEDIA}/_cache/`
- **Logs**: `${MEDIA}/gartan_debug.log`
- **Crew Details**: `${MEDIA}/crew_details.local`

## Default Behavior

If `MEDIA` is not set, the current directory (`.`) is used as the default.

## Docker Usage

The Docker configuration automatically sets `MEDIA=/app/data` and mounts a volume for persistence:

```yaml
environment:
  - MEDIA=/app/data
volumes:
  - gartan_data:/app/data
```

## Local Development

For local development, you can either:

1. Use the default (files in current directory):
   ```bash
   python run_bot.py --max-days 1
   ```

2. Specify a custom media directory:
   ```bash
   export MEDIA=/home/user/gartan_data
   python run_bot.py --max-days 1
   ```

The media directory will be created automatically if it doesn't exist.
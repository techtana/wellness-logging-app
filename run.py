#!/usr/bin/env python
"""Clinical Intelligence System - Main Entry Point"""
import sys
import argparse
from src.api import create_app
from src.config import config


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Clinical Intelligence System - AI-powered therapeutic communication analysis'
    )
    parser.add_argument(
        '--host',
        default=config.API_HOST,
        help=f'API host (default: {config.API_HOST})'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=config.API_PORT,
        help=f'API port (default: {config.API_PORT})'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )

    args = parser.parse_args()

    # Create Flask app
    app = create_app()

    # Run server
    print(f"""
    ╔═══════════════════════════════════════════════════════════════╗
    ║     Clinical Intelligence System - Therapeutic AI Engine      ║
    ║                     Version 1.0.0                             ║
    ╚═══════════════════════════════════════════════════════════════╝

    Starting API server...
    📊 Server: http://{args.host}:{args.port}
    📖 API Docs: http://{args.host}:{args.port}/api/v1/docs
    💚 Health: http://{args.host}:{args.port}/health

    Ready to analyze therapeutic sessions!
    """)

    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug or config.DEBUG,
        use_reloader=args.debug or config.DEBUG
    )


if __name__ == '__main__':
    main()

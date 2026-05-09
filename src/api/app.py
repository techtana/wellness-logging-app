"""Flask application — Clinical Intelligence System API"""
import io
import json
import os
import tempfile
import logging
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify, render_template, Response, stream_with_context, send_file

from src.main import TherapeuticCommunicationAnalyzer
from src.config import config
from src.ai.settings import AISettings
from src.ai.analyzer import AIAnalyzer
from src.knowledge_base.manager import KnowledgeBaseManager
from src.transcription.settings import TranscriptionSettings
from src.prompts.manager import PromptManager
from src.sessions.manager import SessionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_ALLOWED_AUDIO = {'.mp3', '.wav', '.m4a', '.ogg', '.webm', '.flac', '.mp4', '.aac'}
_ALLOWED_KB_FILES = {'.txt', '.pdf', '.md'}


def _extract_text(file_obj, file_type: str) -> str:
    """Extract plain text from an uploaded file (PDF or text)."""
    if file_type == 'pdf':
        data = file_obj.read()
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=data, filetype="pdf")
            return "\n".join(page.get_text() for page in doc)
        except ImportError:
            pass
        try:
            from pdfminer.high_level import extract_text_to_fp
            out = io.StringIO()
            extract_text_to_fp(io.BytesIO(data), out)
            return out.getvalue()
        except ImportError:
            pass
        return data.decode('utf-8', errors='replace')
    else:
        return file_obj.read().decode('utf-8', errors='replace')


def _build_analyzer(ai_settings: AISettings, kb_manager: KnowledgeBaseManager) -> TherapeuticCommunicationAnalyzer:
    provider = ai_settings.create_provider()
    ai_analyzer = AIAnalyzer(provider, kb_manager) if provider else None
    return TherapeuticCommunicationAnalyzer(ai_analyzer=ai_analyzer)


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(_ROOT, 'templates'),
        static_folder=os.path.join(_ROOT, 'static'),
    )
    app.config.update(DEBUG=config.DEBUG, TESTING=config.TESTING, JSON_SORT_KEYS=False)

    # Shared service instances
    ai_settings = AISettings()
    transcription_settings = TranscriptionSettings()
    kb_manager = KnowledgeBaseManager()
    prompt_manager = PromptManager()
    session_manager = SessionManager()
    analyzer_ref = {'instance': _build_analyzer(ai_settings, kb_manager)}

    def get_analyzer():
        return analyzer_ref['instance']

    def refresh_analyzer():
        analyzer_ref['instance'] = _build_analyzer(ai_settings, kb_manager)

    # ── UI ─────────────────────────────────────────────────
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/health')
    def health():
        prov = ai_settings._data.get('provider', 'none')
        return jsonify({
            'status': 'healthy',
            'service': 'Clinical Intelligence System',
            'ai_provider': prov,
            'timestamp': datetime.now().isoformat()
        }), 200

    # ── Analysis ────────────────────────────────────────────
    @app.route('/api/v1/analyze', methods=['POST'])
    def analyze_session():
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        transcript = data.get('transcript')
        if not transcript:
            return jsonify({'error': 'Missing transcript field'}), 400
        session_id = data.get('session_id', f"session_{datetime.now().timestamp()}")
        patient_id = data.get('patient_id', 'anonymous')
        try:
            result = get_analyzer().analyze_session(transcript, session_id, patient_id)
            return jsonify(result), 200 if result.get('status') == 'success' else 400
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            return jsonify({'error': 'Analysis failed', 'message': str(e)}), 500

    @app.route('/api/v1/analyze/section', methods=['POST'])
    def analyze_section():
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data'}), 400
        section = data.get('section')
        transcript = data.get('transcript')
        if not section or not transcript:
            return jsonify({'error': 'Required: section, transcript'}), 400

        kb_id = data.get('kb_id')
        custom_instruction = None
        if kb_id:
            inst = kb_manager.get_by_id_with_files(kb_id)
            if inst:
                custom_instruction = inst['prompt']

        provider = ai_settings.create_provider()
        if not provider:
            return jsonify({'error': 'No AI provider configured. Set one in Settings.'}), 503

        from src.ai.analyzer import AIAnalyzer as _AIAnalyzer
        ai = _AIAnalyzer(provider, kb_manager)

        try:
            if section == 'sentiment':
                result = ai.analyze_emotions(transcript, custom_instruction=custom_instruction)
            elif section == 'themes':
                result = ai.analyze_themes(transcript, custom_instruction=custom_instruction)
            elif section == 'dynamics':
                result = ai.analyze_dynamics(transcript, custom_instruction=custom_instruction)
            elif section == 'clinical_report':
                session_id = data.get('session_id', 'unknown')
                patient_id = data.get('patient_id', 'anonymous')
                sentiment = data.get('sentiment', {})
                thematic = data.get('thematic', {})
                relational = data.get('relational', {})
                result = ai.generate_report_sections(
                    transcript, session_id, patient_id,
                    sentiment, thematic, relational,
                    custom_instruction=custom_instruction
                )
            else:
                return jsonify({'error': f'Unknown section: {section}'}), 400
            return jsonify({'section': section, 'result': result}), 200
        except Exception as e:
            logger.error(f"Section analysis error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/v1/analyze/batch', methods=['POST'])
    def analyze_batch():
        data = request.get_json()
        if not data or 'sessions' not in data:
            return jsonify({'error': 'Missing sessions field'}), 400
        sessions = data.get('sessions', [])
        if not sessions:
            return jsonify({'error': 'sessions array is empty'}), 400
        try:
            results = get_analyzer().analyze_sessions_batch(sessions)
            return jsonify({'status': 'success', 'sessions_analyzed': len(results), 'results': results}), 200
        except Exception as e:
            logger.error(f"Batch error: {e}")
            return jsonify({'error': 'Batch failed', 'message': str(e)}), 500

    # ── Transcription ───────────────────────────────────────
    @app.route('/api/v1/transcribe', methods=['POST'])
    def transcribe_audio():
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file in request (field name: audio)'}), 400

        audio_file = request.files['audio']
        suffix = Path(audio_file.filename or 'audio.wav').suffix.lower()
        if suffix not in _ALLOWED_AUDIO:
            return jsonify({'error': f'Unsupported audio format. Allowed: {", ".join(_ALLOWED_AUDIO)}'}), 400

        service = transcription_settings.create_service()
        if service is None:
            return jsonify({'error': 'No transcription provider configured. Set one in Settings.'}), 503

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                audio_file.save(tmp.name)
                tmp_path = tmp.name
            result = service.transcribe(tmp_path)
            return jsonify({
                'status': 'success',
                'text': result.text,
                'language': result.language,
                'segments': result.segments
            })
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return jsonify({'error': 'Transcription failed', 'message': str(e)}), 500
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @app.route('/api/v1/transcribe/stream', methods=['POST'])
    def transcribe_audio_stream():
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file in request (field name: audio)'}), 400

        audio_file = request.files['audio']
        suffix = Path(audio_file.filename or 'audio.wav').suffix.lower()
        if suffix not in _ALLOWED_AUDIO:
            return jsonify({'error': f'Unsupported audio format. Allowed: {", ".join(_ALLOWED_AUDIO)}'}), 400

        service = transcription_settings.create_service()
        if service is None:
            def _no_provider():
                yield f"data: {json.dumps({'type': 'error', 'message': 'No transcription provider configured. Set one in Settings.'})}\n\n"
            return Response(stream_with_context(_no_provider()), content_type='text/event-stream')

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            audio_file.save(tmp.name)
            tmp_path = tmp.name

        def generate():
            try:
                for event in service.transcribe_stream(tmp_path):
                    yield f"data: {json.dumps(event)}\n\n"
            except Exception as e:
                logger.error(f"Stream transcription error: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        return Response(
            stream_with_context(generate()),
            content_type='text/event-stream',
            headers={'X-Accel-Buffering': 'no', 'Cache-Control': 'no-cache'},
        )

    # ── AI Settings ─────────────────────────────────────────
    @app.route('/api/v1/settings/ai', methods=['GET'])
    def get_ai_settings():
        return jsonify(ai_settings.get_safe())

    @app.route('/api/v1/settings/ai', methods=['PUT'])
    def update_ai_settings():
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data'}), 400
        ai_settings.update(data)
        refresh_analyzer()
        return jsonify(ai_settings.get_safe())

    # ── Ollama model list ────────────────────────────────────
    @app.route('/api/v1/ollama/models', methods=['GET'])
    def list_ollama_models():
        import urllib.request
        host = request.args.get('host', 'http://localhost:11434').rstrip('/')
        try:
            req = urllib.request.Request(f'{host}/api/tags', headers={'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read())
            models = [m['name'] for m in data.get('models', [])]
            return jsonify({'models': models})
        except Exception as e:
            return jsonify({'models': [], 'error': str(e)}), 200

    # ── Transcription Settings ──────────────────────────────
    @app.route('/api/v1/settings/transcription', methods=['GET'])
    def get_transcription_settings():
        return jsonify(transcription_settings.get_safe())

    @app.route('/api/v1/settings/transcription', methods=['PUT'])
    def update_transcription_settings():
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data'}), 400
        transcription_settings.update(data)
        return jsonify(transcription_settings.get_safe())

    # ── Knowledge Base ──────────────────────────────────────
    @app.route('/api/v1/kb/instructions', methods=['GET'])
    def list_instructions():
        return jsonify({'instructions': kb_manager.list()})

    @app.route('/api/v1/kb/instructions', methods=['POST'])
    def create_instruction():
        data = request.get_json()
        if not data or not all(k in data for k in ('name', 'category', 'prompt')):
            return jsonify({'error': 'Required fields: name, category, prompt'}), 400
        inst = kb_manager.create(data['name'], data['category'], data['prompt'])
        return jsonify(inst), 201

    @app.route('/api/v1/kb/instructions/<inst_id>', methods=['GET'])
    def get_instruction(inst_id):
        inst = kb_manager.get_by_id(inst_id)
        return jsonify(inst) if inst else (jsonify({'error': 'Not found'}), 404)

    @app.route('/api/v1/kb/instructions/<inst_id>', methods=['PUT'])
    def update_instruction(inst_id):
        data = request.get_json() or {}
        inst = kb_manager.update(inst_id, **{k: data[k] for k in ('name', 'category', 'prompt', 'enabled') if k in data})
        return jsonify(inst) if inst else (jsonify({'error': 'Not found'}), 404)

    @app.route('/api/v1/kb/instructions/<inst_id>', methods=['DELETE'])
    def delete_instruction(inst_id):
        ok = kb_manager.delete(inst_id)
        return jsonify({'deleted': ok}) if ok else (jsonify({'error': 'Not found'}), 404)

    @app.route('/api/v1/kb/reset', methods=['POST'])
    def reset_kb():
        kb_manager.reset()
        return jsonify({'message': 'Knowledge base reset to defaults', 'instructions': kb_manager.list()})

    @app.route('/api/v1/kb/instructions/<inst_id>/files', methods=['GET'])
    def list_kb_files(inst_id):
        inst = kb_manager.get_by_id(inst_id)
        if not inst:
            return jsonify({'error': 'Not found'}), 404
        return jsonify({'files': kb_manager.list_files(inst_id)})

    @app.route('/api/v1/kb/instructions/<inst_id>/files', methods=['POST'])
    def upload_kb_file(inst_id):
        inst = kb_manager.get_by_id(inst_id)
        if not inst:
            return jsonify({'error': 'Not found'}), 404
        if 'file' in request.files:
            f = request.files['file']
            filename = f.filename or 'file.txt'
            suffix = Path(filename).suffix.lower()
            if suffix not in _ALLOWED_KB_FILES:
                return jsonify({'error': f'Unsupported file type. Allowed: {", ".join(_ALLOWED_KB_FILES)}'}), 400
            file_type = 'pdf' if suffix == '.pdf' else 'text'
            content = _extract_text(f, file_type)
        else:
            body = request.get_json() or {}
            filename = body.get('filename', 'content.txt')
            content = body.get('content_text', '')
            file_type = body.get('file_type', 'text')
        if not content or not content.strip():
            return jsonify({'error': 'File is empty or could not be read'}), 400
        ok = kb_manager.save_file(inst_id, filename, content, file_type)
        return jsonify({'ok': ok, 'filename': filename})

    @app.route('/api/v1/kb/instructions/<inst_id>/files/<path:filename>', methods=['DELETE'])
    def delete_kb_file(inst_id, filename):
        ok = kb_manager.delete_file(inst_id, filename)
        return jsonify({'deleted': ok}) if ok else (jsonify({'error': 'Not found'}), 404)

    # ── Prompts ─────────────────────────────────────────────
    @app.route('/api/v1/prompts/session', methods=['GET'])
    def get_session_prompts():
        return jsonify({'prompts': prompt_manager.get_session_prompts()})

    @app.route('/api/v1/prompts', methods=['GET'])
    def list_prompts():
        return jsonify({'prompts': prompt_manager.list()})

    @app.route('/api/v1/prompts', methods=['POST'])
    def create_prompt():
        data = request.get_json()
        if not data or 'clinical_text' not in data:
            return jsonify({'error': 'Required field: clinical_text'}), 400
        p = prompt_manager.create(
            category=data.get('category', 'custom'),
            clinical_text=data['clinical_text'],
            rephrased_text=data.get('rephrased_text', ''),
            order=data.get('order'),
        )
        return jsonify(p), 201

    @app.route('/api/v1/prompts/<prompt_id>', methods=['GET'])
    def get_prompt(prompt_id):
        p = prompt_manager.get_by_id(prompt_id)
        return jsonify(p) if p else (jsonify({'error': 'Not found'}), 404)

    @app.route('/api/v1/prompts/<prompt_id>', methods=['PUT'])
    def update_prompt(prompt_id):
        data = request.get_json() or {}
        p = prompt_manager.update(
            prompt_id,
            **{k: data[k] for k in ('category', 'clinical_text', 'rephrased_text', 'enabled', 'order') if k in data}
        )
        return jsonify(p) if p else (jsonify({'error': 'Not found'}), 404)

    @app.route('/api/v1/prompts/<prompt_id>', methods=['DELETE'])
    def delete_prompt(prompt_id):
        ok = prompt_manager.delete(prompt_id)
        return jsonify({'deleted': ok}) if ok else (jsonify({'error': 'Not found'}), 404)

    @app.route('/api/v1/prompts/reset', methods=['POST'])
    def reset_prompts():
        prompt_manager.reset()
        return jsonify({'message': 'Prompts reset to defaults', 'prompts': prompt_manager.list()})

    @app.route('/api/v1/prompts/rephrase', methods=['POST'])
    def rephrase_prompt():
        data = request.get_json()
        if not data or 'clinical_text' not in data:
            return jsonify({'error': 'Required field: clinical_text'}), 400
        provider = ai_settings.create_provider()
        if not provider:
            return jsonify({'error': 'No AI provider configured. Set one in Settings.'}), 503
        system = (
            "You are helping a therapist rewrite a clinical question into warm, conversational language "
            "for a client's self-recording session. Make it feel natural and human — not scripted or clinical. "
            "One or two sentences maximum. Keep the original intent intact. "
            "Respond with only the rephrased text — no quotes, no explanation."
        )
        user_msg = f"Clinical question: {data['clinical_text']}"
        context = data.get('context', '')
        if context:
            user_msg += f"\n\nContext from this session so far:\n{context}"
        try:
            rephrased = provider.complete_text(system, user_msg)
            return jsonify({'rephrased_text': rephrased, 'clinical_text': data['clinical_text']})
        except Exception as e:
            logger.error(f"Rephrase error: {e}")
            return jsonify({'error': str(e)}), 500

    # ── Session bridge note ──────────────────────────────────
    @app.route('/api/v1/session/bridge', methods=['POST'])
    def generate_bridge_note():
        data = request.get_json()
        if not data or 'transcript' not in data:
            return jsonify({'error': 'Required field: transcript'}), 400
        provider = ai_settings.create_provider()
        if not provider:
            return jsonify({'bridge_note': 'Thank you for sharing today. Your responses have been recorded.'})
        transcript = data['transcript']
        client_lines = [t['text'] for t in transcript if t.get('speaker') == 'client' and t.get('text')]
        summary = '\n'.join(f'- {line}' for line in client_lines[:6])
        system = (
            "You are a compassionate therapist writing a brief closing message for a client "
            "at the end of their self-recorded session. Write a warm, encouraging 2-3 sentence note that: "
            "acknowledges what the client shared (without quoting directly), highlights one strength or "
            "insight you observed, and offers gentle encouragement for the week ahead. "
            "Keep it personal, warm, and concise. No clinical language. No lists."
        )
        user_msg = f"The client shared the following during their session:\n{summary}"
        try:
            note = provider.complete_text(system, user_msg)
            return jsonify({'bridge_note': note})
        except Exception as e:
            logger.error(f"Bridge note error: {e}")
            return jsonify({'bridge_note': 'Thank you for taking the time to reflect today. Each session is a step forward.'})

    # ── Sessions ────────────────────────────────────────────
    @app.route('/api/v1/sessions', methods=['POST'])
    def create_session():
        data = request.get_json() or {}
        session_id = data.get('session_id') or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        existing = session_manager.get(session_id)
        if existing:
            return jsonify(existing)
        meta = session_manager.create(session_id)
        return jsonify(meta), 201

    @app.route('/api/v1/sessions', methods=['GET'])
    def list_sessions():
        return jsonify({'sessions': session_manager.list_sessions()})

    @app.route('/api/v1/sessions/<session_id>', methods=['GET'])
    def get_session(session_id):
        s = session_manager.get(session_id)
        return jsonify(s) if s else (jsonify({'error': 'Not found'}), 404)

    @app.route('/api/v1/sessions/<session_id>', methods=['PUT'])
    def update_session(session_id):
        data = request.get_json() or {}
        s = session_manager.update(
            session_id,
            **{k: data[k] for k in ('turns', 'bridge_note', 'status') if k in data}
        )
        return jsonify(s) if s else (jsonify({'error': 'Not found'}), 404)

    @app.route('/api/v1/sessions/<session_id>', methods=['DELETE'])
    def delete_session(session_id):
        ok = session_manager.delete(session_id)
        return jsonify({'deleted': ok}) if ok else (jsonify({'error': 'Not found'}), 404)

    @app.route('/api/v1/sessions/<session_id>/analysis', methods=['PUT'])
    def save_session_analysis(session_id):
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data'}), 400
        s = session_manager.update(session_id, analysis=data)
        return jsonify({'ok': True}) if s else (jsonify({'error': 'Not found'}), 404)

    @app.route('/api/v1/sessions/<session_id>/audio/<filename>', methods=['POST'])
    def upload_session_audio(session_id, filename):
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file (field: audio)'}), 400
        audio_file = request.files['audio']
        data = audio_file.read()
        session_manager.save_audio(session_id, filename, data)
        return jsonify({'ok': True, 'filename': filename})

    @app.route('/api/v1/sessions/<session_id>/audio/<filename>', methods=['GET'])
    def get_session_audio(session_id, filename):
        p = session_manager.get_audio_path(session_id, filename)
        if not p:
            return jsonify({'error': 'Not found'}), 404
        suffix = Path(filename).suffix.lower()
        mime_map = {'.webm': 'audio/webm', '.wav': 'audio/wav', '.mp3': 'audio/mpeg',
                    '.m4a': 'audio/mp4', '.ogg': 'audio/ogg', '.flac': 'audio/flac'}
        mime = mime_map.get(suffix, 'application/octet-stream')
        return send_file(p, mimetype=mime, as_attachment=False)

    @app.route('/api/v1/sessions/<session_id>/transcript.txt', methods=['GET'])
    def download_transcript(session_id):
        text = session_manager.transcript_text(session_id)
        if text is None:
            return jsonify({'error': 'Not found'}), 404
        return Response(
            text,
            mimetype='text/plain; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename="transcript_{session_id}.txt"'}
        )

    @app.route('/api/v1/sessions/<session_id>/report.pdf', methods=['GET'])
    def download_session_report(session_id):
        s = session_manager.get(session_id)
        if not s:
            return jsonify({'error': 'Session not found'}), 404
        try:
            from src.reports.generator import generate_pdf
            pdf_bytes = generate_pdf(s)
            return Response(
                pdf_bytes,
                mimetype='application/pdf',
                headers={'Content-Disposition': f'attachment; filename="report_{session_id}.pdf"'}
            )
        except ImportError as e:
            return jsonify({'error': str(e)}), 503
        except Exception as e:
            logger.error(f"PDF generation error: {e}")
            return jsonify({'error': str(e)}), 500

    # ── Docs ────────────────────────────────────────────────
    @app.route('/api/v1/docs')
    def api_docs():
        return jsonify({
            'service': 'Clinical Intelligence System',
            'version': '2.0.0',
            'endpoints': {
                'analyze': 'POST /api/v1/analyze',
                'transcribe': 'POST /api/v1/transcribe  (multipart: audio file)',
                'ai_settings': 'GET|PUT /api/v1/settings/ai',
                'transcription_settings': 'GET|PUT /api/v1/settings/transcription',
                'kb_instructions': 'GET|POST /api/v1/kb/instructions',
                'kb_instruction': 'GET|PUT|DELETE /api/v1/kb/instructions/<id>',
                'kb_reset': 'POST /api/v1/kb/reset',
            }
        })

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Endpoint not found'}), 404

    @app.errorhandler(500)
    def internal_error(e):
        logger.error(f"Internal error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

    return app

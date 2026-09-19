from __future__ import annotations

import uuid
from flask import Flask, request, jsonify, render_template

from verdict.engine import GameState
from verdict.cases import CASES
from verdict.ai_player import ai_argue

app = Flask(__name__)
games: dict[str, dict] = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/cases")
def list_cases():
    return jsonify({
        k: {"title": v["title"], "charge": v["charge"]}
        for k, v in CASES.items()
    })


@app.route("/api/game/start", methods=["POST"])
def start_game():
    data       = request.json or {}
    case_key   = data.get("case", "espionage")
    mode       = data.get("mode", "pvp")
    model      = data.get("model", "jev-latest")
    max_rounds = int(data.get("max_rounds", 6))
    threshold  = float(data.get("threshold", 0.85))

    if case_key not in CASES:
        return jsonify({"error": f"unknown case '{case_key}'"}), 400

    game_id = str(uuid.uuid4())[:8]
    state = GameState(
        case=CASES[case_key],
        model=model,
        max_rounds=max_rounds,
        win_threshold=threshold,
    )
    games[game_id] = {"state": state, "mode": mode, "case_key": case_key}

    return jsonify({
        "game_id":      game_id,
        "case":         CASES[case_key],
        "mode":         mode,
        "max_rounds":   max_rounds,
        "guilty_prob":  state.guilty_prob,
        "current_role": state.current_role(),
    })


def _result_json(state: GameState, result) -> dict:
    return {
        "role":           result.role,
        "argument":       result.argument,
        "logic":          round(result.logic, 3),
        "evidence":       round(result.evidence, 3),
        "persuasion":     round(result.persuasion, 3),
        "relevant":       round(result.relevant, 3),
        "guilty_prob":    round(result.guilty_prob, 3),
        "guilty_delta":   round(result.guilty_delta, 3),
        "round_num":      result.round_num,
        "finished":       state.finished,
        "winner":         state.winner,
        "current_role":   state.current_role() if not state.finished else None,
    }


@app.route("/api/game/<game_id>/argue", methods=["POST"])
def argue(game_id: str):
    if game_id not in games:
        return jsonify({"error": "game not found"}), 404

    data     = request.json or {}
    argument = data.get("argument", "").strip()
    if not argument:
        return jsonify({"error": "empty argument"}), 400

    state = games[game_id]["state"]
    if state.finished:
        return jsonify({"error": "game finished"}), 400

    result = state.score_argument(argument)
    return jsonify(_result_json(state, result))


@app.route("/api/game/<game_id>/ai-argue", methods=["POST"])
def ai_argue_endpoint(game_id: str):
    if game_id not in games:
        return jsonify({"error": "game not found"}), 404

    state = games[game_id]["state"]
    if state.finished:
        return jsonify({"error": "game finished"}), 400

    role     = state.current_role()
    history  = [{"role": h.role, "argument": h.argument} for h in state.history]
    argument = ai_argue(state.case, history, role)

    result = state.score_argument(argument)
    out    = _result_json(state, result)
    out["ai_generated"] = True
    return jsonify(out)


@app.route("/api/game/<game_id>/state")
def game_state(game_id: str):
    if game_id not in games:
        return jsonify({"error": "game not found"}), 404

    state = games[game_id]["state"]
    return jsonify({
        "guilty_prob":  state.guilty_prob,
        "round_num":    state.round_num,
        "finished":     state.finished,
        "winner":       state.winner,
        "current_role": state.current_role() if not state.finished else None,
        "history": [
            {
                "role":        h.role,
                "argument":    h.argument,
                "logic":       round(h.logic, 3),
                "evidence":    round(h.evidence, 3),
                "persuasion":  round(h.persuasion, 3),
                "guilty_prob": round(h.guilty_prob, 3),
                "guilty_delta":round(h.guilty_delta, 3),
                "round_num":   h.round_num,
            }
            for h in state.history
        ],
    })


if __name__ == "__main__":
    print("\n  VERDICT — AI Courtroom Judge")
    print("  ─────────────────────────────")
    print("  Open: http://localhost:5000\n")
    app.run(debug=False, port=5000)

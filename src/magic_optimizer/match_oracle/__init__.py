from magic_optimizer.match_oracle.api import match_oracle_bp
from magic_optimizer.match_oracle.dck import to_dck
from magic_optimizer.match_oracle.forge import ForgeMatchOracle
from magic_optimizer.match_oracle.forge_runner import (
    ForgeParseError,
    build_forge_sim_command,
    parse_forge_sim_output,
    run_forge_sim,
)
from magic_optimizer.match_oracle.health import forge_available
from magic_optimizer.match_oracle.records import (
    append_match_record,
    match_record_from_result,
)
from magic_optimizer.match_oracle.stub import StubMatchOracle
from magic_optimizer.match_oracle.types import (
    ForgePlayerAI,
    MatchOracle,
    MatchResult,
    PlayerBackend,
)

__all__ = [
    "match_oracle_bp",
    "ForgeMatchOracle",
    "ForgeParseError",
    "ForgePlayerAI",
    "MatchOracle",
    "MatchResult",
    "PlayerBackend",
    "StubMatchOracle",
    "append_match_record",
    "build_forge_sim_command",
    "forge_available",
    "match_record_from_result",
    "parse_forge_sim_output",
    "run_forge_sim",
    "to_dck",
]

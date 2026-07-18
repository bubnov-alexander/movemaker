# Skip outro

## Goal

Exclude the final 60 seconds of a source video from short candidate generation by default, while allowing the value to be changed from YAML or the command line.

## Interface

`RunConfig` gains `skip_outro: float = 60.0`. `config.yaml` accepts `skip_outro`; `movie-shorts create` accepts `--skip-outro SECONDS`. As with `skip_intro`, a supplied CLI value overrides YAML. `0` disables outro exclusion; negative values are rejected in Russian.

## Candidate generation

The pipeline passes the source video duration and `skip_outro` to `build_candidates`. A candidate is retained only when its end time is less than or equal to `media.duration - skip_outro`. If the excluded ending leaves no eligible candidates, the existing insufficient-candidates flow is used without an error.

## Testing

Unit tests cover the default, YAML value, CLI override, negative-value validation, and filtering of candidates that reach the final excluded interval.

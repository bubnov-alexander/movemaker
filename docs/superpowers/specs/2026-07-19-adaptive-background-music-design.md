# Adaptive background music

## Goal

Add two local music tracks to generated shorts. The renderer must automatically choose a track that fits a selected fragment and keep it beneath the source audio, especially dialogue and loud original moments.

## Configuration

Add an optional `background_music` section to the YAML configuration. It contains paths to the `epic` and `calm` tracks, a maximum music volume, a quiet-scene music volume, and the epic-score threshold. If the section or either track is unavailable, rendering preserves the current source-audio-only behaviour.

`epic` is the FindMyName — YA YA track. `calm` is the altyn - tatarka slowed instrumental.

## Selection

For every candidate, calculate a deterministic epic score from existing candidate signals:

- keyword/text score, with action and danger vocabulary contributing most;
- motion score;
- source audio energy and changes in energy;
- the candidate's existing aggregate score.

Candidates at or above the configurable threshold use the epic track. Other candidates use the calm track. The selected track and epic score are written to the run manifest so the result is explainable.

## Rendering and audio mix

The renderer seeks the chosen track to a deterministic offset derived from the candidate, loops it when needed, and trims it to the short duration. FFmpeg mixes it with the original audio.

The background stream has a conservative peak volume. FFmpeg applies sidechain compression using the original audio as the sidechain signal: music ducks while speech or another loud foreground sound is present and recovers smoothly in quieter passages. The original audio is never attenuated by this feature. Output stays AAC audio in the existing MP4 container.

If the source video has no audio, the selected music is still emitted at the conservative volume. If FFmpeg cannot read the configured track, the command fails with a Russian user-facing message that names the unavailable track.

## Interfaces and tests

- Extend parsed configuration and validation for the new optional section.
- Add a small music-selection service with unit tests for epic and calm choices plus missing-config fallback.
- Extend the render command tests to assert input ordering, looping/trimming, sidechain ducking, and original-audio fallback.
- Add an FFmpeg integration test using generated audio fixtures to confirm the output contains audio and can be probed.

## Non-goals

This change does not identify music beats, rewrite subtitles, add remote music services, or infer copyright permissions. Tracks remain local project/user-supplied files.

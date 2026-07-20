from movie_shorts.models import WordTiming


def _timestamp(seconds: float) -> str:
    centiseconds = round(max(seconds, 0) * 100)
    hours, remainder = divmod(centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    return f"{hours}:{minutes:02d}:{remainder // 100:02d}.{remainder % 100:02d}"


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def group_words(words: tuple[WordTiming, ...]) -> list[tuple[WordTiming, ...]]:
    groups: list[list[WordTiming]] = []
    for word in words:
        if not groups:
            groups.append([word])
            continue

        current_group = groups[-1]
        previous_word = current_group[-1]
        group_duration = word.end - current_group[0].start
        pause = word.start - previous_word.end
        if len(current_group) == 3 or pause > 0.45 or group_duration > 2.5:
            groups.append([word])
        else:
            current_group.append(word)
    return [tuple(group) for group in groups]


def build_ass(words: tuple[WordTiming, ...], video_start: float) -> str:
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,Arial,92,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,6,2,2,60,60,140,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    events = []
    for group in group_words(words):
        start = group[0].start - video_start
        end = group[-1].end - video_start
        parts: list[str] = []
        for index, word in enumerate(group):
            if index > 0:
                pause = word.start - group[index - 1].end
                if pause > 0:
                    parts.append(f"{{\\k{max(round(pause * 100), 1)}}}")
            duration = max(round((word.end - word.start) * 100), 1)
            parts.append(f"{{\\k{duration}}}{_escape(word.text)}")
        text = " ".join(parts)
        events.append(
            f"Dialogue: 0,{_timestamp(start)},{_timestamp(end)},Default,,0,0,0,,{text}"
        )
    return header + "\n".join(events) + ("\n" if events else "")

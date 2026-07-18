from movie_shorts.models import WordTiming


def _timestamp(seconds: float) -> str:
    centiseconds = round(max(seconds, 0) * 100)
    hours, remainder = divmod(centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    return f"{hours}:{minutes:02d}:{remainder // 100:02d}.{remainder % 100:02d}"


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def build_ass(words: tuple[WordTiming, ...], video_start: float) -> str:
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,Arial,72,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,4,1,2,60,60,140,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    events = []
    for word in words:
        start = word.start - video_start
        end = word.end - video_start
        duration_centiseconds = max(round((end - start) * 100), 1)
        text = _escape(word.text)
        events.append(
            f"Dialogue: 0,{_timestamp(start)},{_timestamp(end)},Default,,0,0,0,,{{\\c&H00FFFF&\\k{duration_centiseconds}}}{text}"
        )
    return header + "\n".join(events) + ("\n" if events else "")

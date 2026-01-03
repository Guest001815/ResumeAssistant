import sys
from pathlib import Path

# 允许相对导入 backend 包
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from editor_agent import EditorAgent  # type: ignore


def main():
    agent = EditorAgent.__new__(EditorAgent)  # 不调用 __init__，避免外部依赖

    cases = [
        ("空字符串", ""),
        ("空白", "   "),
        ("自然语言", "请帮我更新简历"),
        ("半截 JSON", '{"a": 1,'),
        ("列表", '["x", "y"]'),
        ("字符串 JSON", '"hello"'),
        ("数字 JSON", "42"),
        ("合法字典", '{"a": 1, "b": "x"}'),
    ]

    for name, raw in cases:
        parsed, error = agent._safe_json_args(raw)  # type: ignore
        print(f"{name}: 输入={raw!r} -> 输出={parsed!r}, 错误={error!r}")

    # 简单断言：非法输入应返回 {} 且带有错误信息
    assert agent._safe_json_args("")[0] == {}
    assert agent._safe_json_args("")[1] is not None

    assert agent._safe_json_args("not json")[0] == {}
    assert agent._safe_json_args("not json")[1] is not None

    assert agent._safe_json_args('["x"]')[0] == {}
    assert agent._safe_json_args('"x"')[0] == {}
    assert agent._safe_json_args("1")[0] == {}

    # 合法字典应保持原样
    ok, error = agent._safe_json_args('{"a": 1}')
    assert isinstance(ok, dict) and ok.get("a") == 1
    assert error is None

    print("全部用例通过")


if __name__ == "__main__":
    main()

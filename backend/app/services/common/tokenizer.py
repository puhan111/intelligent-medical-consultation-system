import jieba


def segment(text: str) -> str:
    """
    对中文文本分词，返回空格分隔的词序列，用于构建 tsvector/tsquery。
    Postgres 默认的 'simple' 分词器不支持中文分词（会把整段连续汉字当作一个 token），
    因此在应用层用 jieba 预分词后再交给 to_tsvector/to_tsquery('simple', ...) 处理。
    """
    if not text:
        return ""
    tokens = [t.strip() for t in jieba.cut(text) if t.strip()]
    return " ".join(tokens)

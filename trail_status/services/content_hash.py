import hashlib
from typing import Optional

from trafilatura import extract


def calculate_content_hash(scraped_text: str) -> str:
    """
    スクレイピングしたHTMLからtrafilaturaで抽出した内容のハッシュ値を計算
    
    Args:
        scraped_text: スクレイピングしたHTML文字列
        
    Returns:
        str: SHA256ハッシュ値（64文字）
    """
    # trafilaturaで正規化されたテキストを抽出
    normalized_content = extract(scraped_text, include_comments=False, include_tables=True)
    
    if not normalized_content:
        # 抽出できない場合は空文字列として扱う
        normalized_content = ""
    
    # UTF-8エンコードしてハッシュ計算
    return hashlib.sha256(normalized_content.encode('utf-8')).hexdigest()


def has_content_changed(current_html: str, previous_hash: Optional[str]) -> tuple[bool, str]:
    """
    コンテンツが変更されているかをハッシュで判定
    
    Args:
        current_html: 現在スクレイピングしたHTML
        previous_hash: 前回のハッシュ値（None の場合は初回）
        
    Returns:
        tuple[bool, str]: (変更フラグ, 新しいハッシュ値)
    """
    current_hash = calculate_content_hash(current_html)
    
    # 初回スクレイピングまたはハッシュが異なる場合は変更あり
    has_changed = previous_hash is None or current_hash != previous_hash
    
    return has_changed, current_hash
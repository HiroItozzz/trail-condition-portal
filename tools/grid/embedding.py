from pathlib import Path

import pandas as pd
from google import genai
from google.genai import types
from sklearn.metrics.pairwise import cosine_similarity

client = genai.Client()
texts = [
    "雲取山",
    "酉谷山・雲取山",
    "小雲取山",
    "雲取山荘",
    "鷹ノ巣山",
    "御岳山・大岳山",
    "大岳山",
    """東京都西多摩郡檜原村、奥多摩町の境界、奥多摩山域にある標高1,266.5mの山。標高はさして高くないが、個性的な山容を備えた奥多摩の名峰である。日本二百名山及び花の百名山の一つに数えられる。多様な登山コースがあり、初心者から経験者まで幅広く楽しめる山である。""",
    "御前山",
    """奥多摩湖南岸、奥多摩主脈の中心に聳える山。遠くから見た山容・姿が美しい。カタクリの自生地。田中澄江の著作「花の百名山」に春のカタクリの花の名所として取り上げられている。カラマツが黄葉する秋、山頂一帯は黄金色に染まる[2]。南の檜原村側は特に植林が多い。山頂は広いが、眺望はあまりない。対岸に石尾根が位置する。小河内ダム堰堤に、登山道のひとつ大ブナ尾根の入り口がある。道中、奥多摩湖を南東から見下ろせる。また、奥多摩都民の森（通称、体験の森）が北側斜面にある。 東京都の奥多摩山域の代表的な山の一つで、多摩百山に選ばれている。""",
    "三頭山",
    "川苔山・本仁田山",
]

result = client.models.embed_content(
    model="gemini-embedding-001", contents=texts, config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY")
)

# Create a 3x3 table to show the similarity matrix
df = pd.DataFrame(
    cosine_similarity([e.values for e in result.embeddings]),
    index=texts,
    columns=texts,
)

print(df)

(Path.cwd() / "tools/embedding_sample_2.csv").write_text(df.to_csv(encoding="utf-8"))

# uv run python -m tools.embedding

import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams["font.family"] = "Source Han Code JP"

fig, ax = plt.subplots(figsize=(8, 6))
sns.heatmap(df, annot=True, fmt=".3f", ax=ax)
plt.tight_layout()
plt.savefig("tools/similarity_matrix_2.png")

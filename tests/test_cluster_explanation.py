import numpy as np
import pandas as pd

from analysis.cluster_explanation import explain_clusters


def test_cluster_explanation_returns_description_for_each_cluster():
    df = pd.DataFrame(
        {
            "revenue": [100, 120, 130, 900, 950, 980],
            "quantity": [1, 2, 1, 8, 9, 10],
            "price": [100, 60, 130, 112, 105, 98],
        }
    )
    labels = np.array([0, 0, 0, 1, 1, 1])

    result = explain_clusters(df, labels, ["revenue", "quantity", "price"])

    assert len(result) == 2
    assert result[0].description
    assert result[0].recommendations
    assert result[1].top_features

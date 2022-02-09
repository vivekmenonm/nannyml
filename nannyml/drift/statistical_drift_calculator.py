#  Author:   Niels Nuyttens  <niels@nannyml.com>
#
#  License: Apache Software License 2.0

"""Statistical drift calculation using `Kolmogorov-Smirnov` and `chi2-contingency` tests."""
import itertools
from typing import Any, Dict, List, Union

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, ks_2samp

from nannyml.chunk import Chunk
from nannyml.drift._base import BaseDriftCalculator, ChunkerPreset
from nannyml.metadata import ModelMetadata


class StatisticalDriftCalculator(BaseDriftCalculator):
    """A drift calculator that relies on statistics to detect drift."""

    def _calculate_drift(
        self, reference_chunks: List[Chunk], analysis_chunks: List[Chunk], model_metadata: ModelMetadata
    ) -> pd.DataFrame:
        # Get lists of categorical <-> categorical features
        categorical_column_names = [f.column_name for f in model_metadata.categorical_features]
        continuous_column_names = [f.column_name for f in model_metadata.continuous_features]

        # Map reference_chunks to analysis_chunks
        mapped_chunks = _map_by_index(reference_chunks, analysis_chunks)

        res = pd.DataFrame()
        # Calculate chunk-wise drift statistics.
        # Append all into resulting DataFrame indexed by chunk key.
        for ref_chunk, ana_chunk in mapped_chunks.items():
            chunk_drift: Dict[str, Any] = {'chunk': ana_chunk.key}

            cat_cols_ana = list(set(ana_chunk.data.columns) & set(categorical_column_names))
            for col in cat_cols_ana:
                statistic, p_value, _, _ = chi2_contingency(
                    pd.concat([ref_chunk.data[col].value_counts(), ana_chunk.data[col].value_counts()], axis=1)
                )
                chunk_drift[f'{col}_statistic'] = [statistic]
                chunk_drift[f'{col}_p_vaLue'] = [np.round(p_value, decimals=3)]

            cont_cols_ana = list(set(ana_chunk.data.columns) & set(continuous_column_names))
            for col in cont_cols_ana:
                statistic, p_value = ks_2samp(ref_chunk.data[col], ana_chunk.data[col])
                chunk_drift[f'{col}_statistic'] = [statistic]
                chunk_drift[f'{col}_p_value'] = [np.round(p_value, decimals=3)]

            res = res.append(pd.DataFrame(chunk_drift))

        res = res.reset_index(drop=True)
        return res


def calculate_statistical_drift(
    reference_data: pd.DataFrame,
    analysis_data: pd.DataFrame,
    model_metadata: ModelMetadata,
    chunk_by: Union[str, ChunkerPreset] = 'size_1000',
) -> pd.DataFrame:
    """Calculates drift using statistical testing.

    This function constructs a StatisticalDriftCalculator and subsequently uses it to calculate drift on a DataFrame
    of analysis data against a reference DataFrame.

    """
    calculator = StatisticalDriftCalculator()
    return calculator.calculate(reference_data, analysis_data, model_metadata, chunk_by=chunk_by)


def _map_by_index(reference_chunks: List[Chunk], analysis_chunks: List[Chunk]) -> Dict[Chunk, Chunk]:
    return {l1: l2 for l1, l2 in itertools.zip_longest(reference_chunks, analysis_chunks, fillvalue=None)}
import os
import logging
import pandas as pd
from config import DATA_PATH, USECOLS, TARGET_COL, ID_COL

logger = logging.getLogger(__name__)

def load_raw_data() -> pd.DataFrame:
    """
    Loads the raw Home Credit data, validates schema, drops duplicates, 
    and checks the target distribution.
    """
    logger.info("Initializing raw data load...")
    
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Dataset not found at expected path: {DATA_PATH}")

    logger.info(f"Reading CSV from {DATA_PATH} using specified columns...")
    df = pd.read_csv(DATA_PATH, usecols=USECOLS)
    
    # Validate TARGET exists and is binary
    if TARGET_COL not in df.columns:
        raise ValueError(f"TARGET column '{TARGET_COL}' not found in loaded data.")
        
    unique_targets = set(df[TARGET_COL].dropna().unique())
    if not unique_targets.issubset({0, 1}):
        raise ValueError(f"TARGET column contains non-binary invalid values: {unique_targets}")
        
    # Deduplicate by primary key
    initial_len = len(df)
    df = df.drop_duplicates(subset=[ID_COL])
    dropped_count = initial_len - len(df)
    if dropped_count > 0:
        logger.warning(f"Dropped {dropped_count} duplicate rows based on '{ID_COL}'.")
        
    # Calculate distributions
    total_samples = len(df)
    default_count = df[TARGET_COL].sum()
    non_default_count = total_samples - default_count
    default_rate = default_count / total_samples
    
    logger.info(f"Loaded {total_samples} distinct applicants.")
    logger.info(f"Class Distribution -> Repaid/Good (0): {non_default_count}, Default/Bad (1): {default_count}")
    logger.info(f"Raw Base Default Rate: {default_rate:.2%}")
    
    # Rate bounds warning
    if default_rate < 0.03 or default_rate > 0.40:
        logger.warning(f"CRITICAL: Default rate ({default_rate:.2%}) is outside expected bounds of [3%, 40%].")
        
    return df

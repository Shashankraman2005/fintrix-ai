import pandas as pd
import logging
import joblib
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OrdinalEncoder
from config import TRAIN_SIZE, VAL_SIZE, TEST_SIZE, RANDOM_SEED, ID_COL, TARGET_COL

logger = logging.getLogger(__name__)

def split_data(df: pd.DataFrame):
    """
    Splits the dataset into Train, Val, and Test sequentially while asserting strict default rate stratifications.
    """
    logger.info("Splitting dataset into train/val/test using configured ratios...")
    
    # Ensure ID_COL and TARGET_COL are not features
    drop_cols = [TARGET_COL]
    if ID_COL in df.columns:
        drop_cols.append(ID_COL)
        
    X = df.drop(columns=drop_cols)
    y = df[TARGET_COL]
    
    # Multi-stage split
    rem_size = VAL_SIZE + TEST_SIZE
    # 1. Split Training vs Remainder
    X_train, X_rem, y_train, y_rem = train_test_split(
        X, y, train_size=TRAIN_SIZE, random_state=RANDOM_SEED, stratify=y
    )
    
    # 2. Split Validation vs Test using relative ratio
    val_ratio_of_rem = VAL_SIZE / rem_size
    X_val, X_test, y_val, y_test = train_test_split(
        X_rem, y_rem, train_size=val_ratio_of_rem, random_state=RANDOM_SEED, stratify=y_rem
    )
    
    total = len(df)
    logger.info(f"Train size: {len(X_train)} ({len(X_train)/total:.1%})")
    logger.info(f"Val size:   {len(X_val)} ({len(X_val)/total:.1%})")
    logger.info(f"Test size:  {len(X_test)} ({len(X_test)/total:.1%})")
    
    # Rate assertions logic
    rate_train = y_train.mean()
    rate_val = y_val.mean()
    rate_test = y_test.mean()
    
    logger.info(f"Stratified Default Rates -> Train: {rate_train:.4f}, Val: {rate_val:.4f}, Test: {rate_test:.4f}")
    
    # Hard assert <= 1% point divergence across splits (0.01)
    train_val_diff = abs(rate_train - rate_val)
    train_test_diff = abs(rate_train - rate_test)
    assert train_val_diff < 0.01, f"CRITICAL: Train and Val default rates diverge by {train_val_diff:.4f}"
    assert train_test_diff < 0.01, f"CRITICAL: Train and Test default rates diverge by {train_test_diff:.4f}"
    
    return X_train, X_val, X_test, y_train, y_val, y_test


def build_preprocessor(X_train: pd.DataFrame) -> ColumnTransformer:
    """
    Builds the imputation and encoding pipelines strictly derived from config expectations.
    """
    logger.info("Building ColumnTransformer preprocessor pipeline...")
    
    potential_cats = ['NAME_CONTRACT_TYPE', 'NAME_EDUCATION_TYPE', 'OCCUPATION_TYPE']
    cat_cols = [c for c in potential_cats if c in X_train.columns]
    num_cols = [c for c in X_train.columns if c not in cat_cols]
    
    # Numeric Pipeline -> median imputation
    num_pipeline = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median"))
    ])
    
    # Categorical Pipeline -> mode imputation + strict ordinal tracking
    cat_pipeline = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1))
    ])
    
    transformers = [("num", num_pipeline, num_cols)]
    if cat_cols:
        transformers.append(("cat", cat_pipeline, cat_cols))
        
    preprocessor = ColumnTransformer(
        transformers=transformers,
        remainder="drop",
        verbose_feature_names_out=False
    )
    
    return preprocessor


def fit_and_transform(preprocessor: ColumnTransformer, X_train: pd.DataFrame, X_val: pd.DataFrame, X_test: pd.DataFrame):
    """
    Fits exclusively on X_train. Transforms all matrices, returns formatted pandas DataFrames.
    """
    logger.info("Fitting preprocessor on training data ONLY...")
    
    # FIT + TRANSFORM on Train precisely
    X_train_transformed = preprocessor.fit_transform(X_train)
    
    # TRANSFORM ONLY on Val and Test
    logger.info("Transforming validation and test validation datasets...")
    X_val_transformed = preprocessor.transform(X_val)
    X_test_transformed = preprocessor.transform(X_test)
    
    # Reconstruct pandas dfs for downstream stability
    feature_names = preprocessor.get_feature_names_out()
    
    X_train_df = pd.DataFrame(X_train_transformed, columns=feature_names, index=X_train.index)
    X_val_df = pd.DataFrame(X_val_transformed, columns=feature_names, index=X_val.index)
    X_test_df = pd.DataFrame(X_test_transformed, columns=feature_names, index=X_test.index)
    
    return X_train_df, X_val_df, X_test_df


def save_preprocessor(preprocessor: ColumnTransformer, path: str) -> None:
    logger.info(f"Saving preprocessor to {path}...")
    joblib.dump(preprocessor, path)


def load_preprocessor(path: str) -> ColumnTransformer:
    logger.info(f"Loading preprocessor from {path}...")
    return joblib.load(path)

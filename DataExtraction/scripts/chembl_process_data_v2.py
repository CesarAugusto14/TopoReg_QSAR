# -*- coding: utf-8 -*-
"""
Created on %(date)s

@author: %(username)s

add the standardization.
split for chemprop at here.
"""

import argparse
import os
from os.path import join as pj
import numpy as np
import pandas as pd


from rdkit import Chem
from rdkit.Chem.EnumerateStereoisomers import EnumerateStereoisomers
from chembl_structure_pipeline import standardize_mol, get_parent_mol

# PATH : target dir.
#%%  Save target csv to txt
def process_target_df(df: pd.DataFrame) -> pd.DataFrame:
    # process single DF
    # Select specific measure types: IC50, EC50, Ki.
    value_selection = df["Standard Type"].map(lambda x: x in ["IC50", "EC50", "Ki"])
    df = df.loc[value_selection]
    # drop records wo\ measures
    df = df.dropna(axis=0, subset=["Standard Units"])
    # drop duplicated. Keep uniques or duplicated but is IC50. Then drop duplicated IC50
    keeps = ~df.index.duplicated() | (df["Standard Type"] == "IC50")
    df = df.loc[keeps]
    df = df.loc[~df.index.duplicated()]
    # drop mols wo\ smiles
    df = df.dropna(axis=0, subset=["Smiles"])
    df["Molecular Weight"] = df["Molecular Weight"].astype(float)
    # keep small molecules only. https://www.nuventra.com/resources/blog/small-molecules-versus-biologics/#:~:text=Compared%20to%20biologics%2C%20small%20molecule,or%201%20kilodalton%20%5BkDa%5D.
    small = df['Molecular Weight'] <= 1000
    df = df.loc[small]


    # Target value is pChEMBL. if pChEMBL is NaN because standard value is too large:
    max_val = df["Standard Value"].max()
    for idx, item in df.iterrows():  # 补全极大 e.g. > 10000nM 的 NaN
        if np.isnan(item['pChEMBL Value']):
            if item["Standard Units"] != 'nM':
                continue
            if (
                item["Standard Value"] == max_val and\
                item["Standard Units"] == 'nM'
            ):
                df.loc[idx, 'pChEMBL Value'] = - np.log10(max_val * 1e-9)
                # item["pChEMBL Value"] = - np.log10(max_val * 1e-9)
    df = df.dropna(axis=0, subset=["pChEMBL Value"])

    # standardization: standardize, remove salt.
    n_isomers = []
    new_smiles = []
    for idx, item in df.iterrows():  # 立体异构体数
        sml = item["Smiles"]
        # raw
        m0 = Chem.MolFromSmiles(sml)
        n_isomers.append(len(tuple(EnumerateStereoisomers(m0))))
        # need not remove H?
        # standardize
        m2 = standardize_mol(m0)
        # get parent
        m3 = get_parent_mol(m2)[0]
        new_smiles.append(Chem.MolToSmiles(m3))
    df['n_isomers'] = n_isomers
    df['Smiles'] = new_smiles

    # added 1/29/2022, remove duplicated SMILES
    df = df.drop_duplicates(subset='Smiles')

    r_df = df[["Smiles", 
               "Standard Type", 
               "Standard Relation", 
               "Standard Value", 
               "Standard Units", 
               "pChEMBL Value", 
               "Assay ChEMBL ID", 
               "Target ChEMBL ID", 
               "n_isomers"]].dropna(axis=0)
    r_df.index.name = "Compound_ID"
    return r_df


def process_target_file(target_path) -> None:
    # execute args
    print("Process data in", target_path)
    tsv = [x for x in os.listdir(target_path) if x.endswith(".tsv")]
    print(len(tsv))
    assert len(tsv) == 1
    df = pd.read_table(pj(target_path, tsv[0]), index_col=0)
    p_df = process_target_df(df)
    p_df.to_csv(pj(target_path, "data.txt"), sep='\t')

    return None


if __name__ == "__main__":
    # parser = argparse.ArgumentParser()
    # parser.add_argument("--path", type=str, default="SampleDatasets/ChEMBL")
    # args = parser.parse_args()
    process_target_file(target_path="SampleDatasets/ChEMBL/CHEMBL278")

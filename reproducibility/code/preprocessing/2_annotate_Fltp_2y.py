# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.7.1
#   kernelspec:
#     display_name: Python rpy2_3
#     language: python
#     name: rpy2_3
# ---

# %%
import scanpy as sc
import anndata as ann
import numpy as np 
import seaborn as sb
import pandas as pd
import pickle
from sklearn import preprocessing as pp
import diffxpy.api as de
import time
from scipy import sparse
#import warnings

import sys  
sys.path.insert(0, '/lustre/groups/ml01/code/karin.hrovatin/mm_pancreas_atlas_rep/code/')
from importlib import reload  
import helper
reload(helper)
import helper as h
from constants import SAVE
import expected_multiplet_rate as emr
reload(emr)
import expected_multiplet_rate as emr
#sc.settings.verbosity = 3

from matplotlib import rcParams
import matplotlib.pyplot as plt

#R interface
import rpy2.rinterface_lib.callbacks
import logging
from rpy2.robjects import pandas2ri
import anndata2ri

rpy2.rinterface_lib.callbacks.logger.setLevel(logging.ERROR)
pandas2ri.activate()
anndata2ri.activate()
# %load_ext rpy2.ipython

# %% language="R"
# library(scran)
# library(biomaRt)
# library(BiocParallel)
# #library(Seurat)

# %%
# Path for saving results - last shared folder by all datasets
shared_folder='/lustre/groups/ml01/workspace/karin.hrovatin/data/pancreas/scRNA/islets_aged_fltp_iCre/rev6/'
UID2='Fltp2y_annotation'

# %% [markdown]
# Load data:

# %%
#Load data
#adata=pickle.load(  open( shared_folder+"data_normalised.pkl", "rb" ) )
adata=h.open_h5ad(shared_folder+"data_normalised.h5ad",unique_id2=UID2)

# %% [markdown]
# ## Add previously generated annotation

# %% [markdown]
# This annotation was not published - done for another lab-internal project by another scientist. It was used only for internal validation and no analyses in this project depend on it.

# %%
# Add previously generated annotation (Maren Buttner)
#adata_preannotated=h.open_h5ad("/lustre/groups/ml01/workspace/karin.hrovatin/data/pancreas/scRNA/salinno_project/rev4/maren/data_endo_final.h5ad",unique_id2=UID2)
adata_preannotated=h.open_h5ad("/lustre/groups/ml01/workspace/karin.hrovatin/data/pancreas/scRNA/islets_aged_fltp_iCre/rev6/maren/data/senis_data_annotated.h5ad",unique_id2=UID2)

# %%
adata_preannotated

# %%
# Match the cell names between preanotated and current dataset
adata_preannotated.obs.index=['-'.join(idx.split('-')[:-1]+[file]) for idx,file in zip(adata_preannotated.obs.index,adata_preannotated.obs.sample_id)]

# %%
# Add pre-prepared cell type annotation to currently used dataset
for annotation in ['cell_type','cell_type_refined']:
    adata.obs['pre_'+annotation]=adata_preannotated.obs.reindex(adata.obs.index)[annotation]
    adata.obs['pre_'+annotation] = adata.obs['pre_'+annotation].cat.add_categories('NA')
    adata.obs['pre_'+annotation].fillna('NA', inplace =True) 

# %% [markdown]
# Pre-annotated cell counts

# %%
# Count of cells per annotation
for annotation in ['cell_type','cell_type_refined']:
    print('pre_'+annotation)
    print(adata.obs['pre_'+annotation].value_counts())

# %%
# Rename annotation columns so that the desired annotation gets the name 'pre_cell_type'
adata.obs.rename(columns={'pre_cell_type':'pre_cell_type_coarse','pre_cell_type_refined':'pre_cell_type'},inplace=True)

# %% [markdown]
# ## Visualisation

# %%
sc.pp.pca(adata, n_comps=30, use_highly_variable=True, svd_solver='arpack')
sc.pl.pca_variance_ratio(adata)

# %%
# Select number of PCs to use
N_PCS=11

# %% [markdown]
# Compare different embeddings based on previously defined annotation. 

# %%
#sc.pp.neighbors(adata,n_pcs = N_PCS,metric='correlation') 
#sc.tl.umap(adata)

# %%
#rcParams['figure.figsize']=(7,7)
#sc.pl.umap(adata,size=10,color=['pre_cell_type'])
#sc.pl.umap(adata,size=10,color=['file'])

# %%
sc.pp.neighbors(adata,n_pcs = N_PCS) 
sc.tl.umap(adata)

# %%
# With default colours the NA  could not be separated well - change the color for NA
pos=len(adata.uns['pre_cell_type_colors'])-1
color='#000000'
if color not in adata.uns['pre_cell_type_colors']:
    adata.uns['pre_cell_type_colors'][pos]=color
else:
    print('Colour is already present:',adata.uns['pre_cell_type_colors'])

# %%
rcParams['figure.figsize']=(7,7)
sc.pl.umap(adata,size=10,color=['pre_cell_type'])
sc.pl.umap(adata,size=10,color=['file'])

# %% [markdown]
# ## Cell cycle
# Performed separately for individual batches.

# %% [markdown]
# ### Seurat/Scanpy - score by G2M and S

# %% [raw]
# # the below few cells needed to be executed only once
# # Extract human cell cycle genes 
# cell_cycle_hs=pd.read_csv('/lustre/groups/ml01/workspace/karin.hrovatin/data/pancreas/gene_lists/cell_cycle_hs_Macosko2015.csv',sep=';')
# cell_cycle_hs=cell_cycle_hs.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

# %% [raw] magic_args="-i cell_cycle_hs -o cell_cycle_mm" language="R"
# # Map human to mouse cell cycle genes and order the dataframe
# # Mapping function taken from https://www.r-bloggers.com/converting-mouse-to-human-gene-names-with-biomart-package/
# genes_hs_mm <- function(human_genes){
# human = useMart("ensembl", dataset = "hsapiens_gene_ensembl")
# mouse = useMart("ensembl", dataset = "mmusculus_gene_ensembl")
#
# genesV2 = getLDS(attributes = c("hgnc_symbol"), filters = "hgnc_symbol", values = human_genes , mart = human, attributesL = c("mgi_symbol"), martL = mouse, uniqueRows=T)
# #print(genesV2)
# return(unique(genesV2[, 'MGI.symbol']))
# }
#
# # Map for each cell cycle phase
# genes<-c()
# phases<-c()
# for(col in colnames(cell_cycle_hs)){
#     human_genes<-unique(cell_cycle_hs[,col])
#     human_genes<-human_genes[!is.na(human_genes)]
#     mouse_genes <- genes_hs_mm(human_genes)
#     print(paste(col,'human:',length(human_genes),'mouse:',length(mouse_genes)))
#     genes<-c(genes,mouse_genes)
#     phases<-c(phases,rep(col,length(mouse_genes)))
# }
# cell_cycle_mm<-data.frame(Gene=genes,Phase=phases)

# %% [raw]
# # Save the mapped data
# cell_cycle_mm.to_csv('/lustre/groups/ml01/workspace/karin.hrovatin/data/pancreas/gene_lists/cell_cycle_mm_Macosko2015.tsv',sep='\t',index=False)

# %%
# Load mouse cell cycle genes
cell_cycle_mm=pd.read_table('/lustre/groups/ml01/workspace/karin.hrovatin/data/pancreas/gene_lists/cell_cycle_mm_Macosko2015.tsv',sep='\t')

# %% [markdown]
# Use cell cycle genes that overlap HVGs (from different batches). Display these genes on HVG plots (with non-phase genes being marked as .NA).
#
# Use G2/M and M gene sets for G2/M annotation and S gene set for S annotation.

# %%
# How many of the cell cycle phase genes are present in HVG and in var and how variable they are
hvg=set(adata.var_names[adata.var.highly_variable])
i=0
rcParams['figure.figsize']=(4,15)
fig,axs=plt.subplots(5)
s_hvg=[]
g2m_hvg=[]
for phase in cell_cycle_mm.Phase.unique():
    genes_phase = set(cell_cycle_mm.query('Phase =="'+phase+'"').Gene)
    overlap_var = set(adata.var_names) & genes_phase
    overlap_hvg = hvg & genes_phase
    print(phase,'N genes:',len(genes_phase),'overlap var:',len(overlap_var),'overlap hvg (all):',len(overlap_hvg))
    phase_df=pd.DataFrame([phase]*len(overlap_var),index=overlap_var,columns=['Phase']).reindex(adata.var_names).fillna('.NA').sort_values('Phase')
    phase_df.loc[overlap_hvg,'Phase']=phase+'_hvg'
    phase_df['mean']=adata.var.means
    phase_df['dispersions_norm']=adata.var.dispersions_norm
    sb.scatterplot(x="mean", y="dispersions_norm", hue="Phase",data=phase_df,ax=axs[i],palette='hls')
    i+=1
    if phase == 'S':
        s_hvg.extend(overlap_hvg)
    if phase in ['G2/M','M']:
        g2m_hvg.extend(overlap_hvg)
        
print('N genes for scoring S:',len(s_hvg),'and G2/M:',len(g2m_hvg))

# %% [markdown]
# Cell cycle annotation

# %%
# Annotated cell cycle per batch
adata.obs['S_score']= np.zeros(adata.shape[0])
adata.obs['G2M_score'] = np.zeros(adata.shape[0])
adata.obs['phase'] = np.zeros(adata.shape[0])

for batch in enumerate(adata.obs['file'].cat.categories):
    batch=batch[1]
    idx = adata.obs.query('file=="'+batch+'"').index
    adata_tmp = adata[idx,:].copy()
    sc.tl.score_genes_cell_cycle(adata_tmp, s_genes=s_hvg, g2m_genes=g2m_hvg,use_raw=False)
    adata.obs.loc[idx,'S_score'] = adata_tmp.obs['S_score']
    adata.obs.loc[idx,'G2M_score'] = adata_tmp.obs['G2M_score']
    adata.obs.loc[idx,'phase'] = adata_tmp.obs['phase']
    
del adata_tmp

# %%
# Count of cells annotated to each phase
adata.obs['phase'].value_counts()

# %% [markdown]
# Display cell cycle score distributions and annotation.

# %%
adata.uns['phase_colors']=['#ff7f0e', '#2ca02c','#46aaf0']

rcParams['figure.figsize']=(5,5)
sb.scatterplot(x='G2M_score',y='S_score',hue='phase',data=adata.obs)
sc.pl.umap(adata, color=['S_score', 'G2M_score'], size=10, use_raw=False)
sc.pl.umap(adata, color=['phase','Mki67'], size=10, use_raw=False)

# %% [markdown]
# #C: There might be some proliferating populations, but it is not very clear as many cells that preobably are not proliferating (low Mki67 expression) are annotated as cycling.

# %% [markdown]
#  ### Cyclone - based on G1, S, and G2/M scores

# %% [markdown]
# Add gene Entrez IDs to adata in order to map genes to cell cycle database.

# %%
# Adata genes for R
genes=adata.var_names

# %% magic_args="-i genes -o gene_ids" language="R"
# # Extract Ensembl gene IDs
# mouse = useMart("ensembl", dataset = "mmusculus_gene_ensembl")
# gene_ids = getBM(attributes = c("mgi_symbol",'ensembl_gene_id'), filters = "mgi_symbol", values = genes , mart = mouse, uniqueRows=FALSE)

# %%
# Add gene ids to adata, use only genes with unique mapped ensembl ids
gene_ids.drop_duplicates(subset='mgi_symbol', keep=False, inplace=True)
gene_ids.index=gene_ids.mgi_symbol
gene_ids=gene_ids.reindex(list(adata.var_names))
adata.var['EID']=gene_ids.ensembl_gene_id

# %%
# Prepare R data for cyclonee
x_mat=adata.X.T
gene_ids=adata.var.EID
batches=adata.obs.file
cells=adata.obs.index

# %% magic_args="-i x_mat -i gene_ids -i batches -i cells -o cyclone_anno" language="R"
# # Cyclone cell scores, calculated separately for each batch
# mm.pairs <- readRDS(system.file("exdata", "mouse_cycle_markers.rds", package="scran"))
# phases<-c()
# s<-c()
# g2m<-c()
# g1<-c()
# cells_order<-c()
# for(batch in unique(batches)){
#     # Select batch data
#     x_mat_batch=x_mat[,batches==batch]
#     print(batch,dim(x_mat_batch[1]))
#     # Scores
#     assignments <- cyclone(x_mat_batch, mm.pairs, gene.names=gene_ids,BPPARAM=MulticoreParam(workers = 16))
#     phases<-c(phases,assignments$phases)
#     s<-c(s,assignments$score$S)
#     g2m<-c(g2m,assignments$score$G2M)
#     g1<-c(g1,assignments$score$G1)
#     # Save cell order
#     cells_order<-c(cells_order,cells[batches==batch])
# }
# cyclone_anno<-data.frame(phase_cyclone=phases,s_cyclone=s,g2m_cyclone=g2m,g1_cyclone=g1)
# rownames(cyclone_anno)<-cells_order

# %%
# Count of cells annotated to each phase
cyclone_anno.phase_cyclone.value_counts()

# %%
# Add cyclone annotation to adata
cyclone_anno=cyclone_anno.reindex(adata.obs.index)
adata.obs=pd.concat([adata.obs,cyclone_anno],axis=1)

# %%
# Plot score distributions and cell assignment on UMAP
rcParams['figure.figsize']=(20,5)
fig,axs=plt.subplots(1,3)
palette=sb.color_palette(['#ff7f0e', '#2ca02c','#46aaf0'])
sb.scatterplot(x='g2m_cyclone',y='s_cyclone',hue='phase_cyclone',data=cyclone_anno,ax=axs[0],palette=palette)
sb.scatterplot(x='g1_cyclone',y='s_cyclone',hue='phase_cyclone',data=cyclone_anno,ax=axs[1],palette=palette)
sb.scatterplot(x='g2m_cyclone',y='g1_cyclone',hue='phase_cyclone',data=cyclone_anno,ax=axs[2],palette=palette)
rcParams['figure.figsize']=(5,5)
sc.pl.umap(adata, color=['s_cyclone', 'g2m_cyclone','g1_cyclone'], size=10, use_raw=False)
adata.uns['phase_cyclone_colors']=['#ff7f0e', '#2ca02c','#46aaf0']
sc.pl.umap(adata, color=['phase_cyclone'], size=10, use_raw=False)

# %% [markdown]
# #C: The cyclone results seem more reliable based on Mki67 expression (above) and embedding.

# %% [markdown]
# ## Sex scores

# %% [markdown]
# Extract expressed genes from X and Y chromosome and score their expression, separately for each batch.

# %% [markdown]
# Add chromosome information:

# %%
# Gene names for R for chromosome assignment
genes=adata.var_names

# %% magic_args="-i genes -o genes_chr" language="R"
# # Chromosome assignment 
#
# mouse = useMart("ensembl", dataset = "mmusculus_gene_ensembl")
# # Return duplicated results - e.g. one gene being annotated to multiple chromosomes
# genes_chr = getBM(attributes = c("mgi_symbol",'chromosome_name'), filters = "mgi_symbol", values = genes , mart = mouse, uniqueRows=F)
#

# %%
# Remove genes annotated to non-standard chromosomes and 
# confirm that each gene is now annotated to only one chromosome
mouse_chromosomes=[str(i) for i in range(1,20)]+['X','Y','MT']
genes_chr_filtered=genes_chr.query('chromosome_name in @mouse_chromosomes')
#Remove duplicated rows (gene was returned multiple times with the same chromosome)
genes_chr_filtered=genes_chr_filtered.drop_duplicates()
print('Each gene has one annotated chromosome:',
      genes_chr_filtered.mgi_symbol.unique().shape[0]==genes_chr_filtered.shape[0])
print('N genes with chromosomes:',genes_chr_filtered.shape[0],'out of',adata.shape[1],'genes')

# %%
# Add chromosomes in adata
genes_chr_filtered.index=genes_chr_filtered.mgi_symbol
genes_chr_filtered=genes_chr_filtered.reindex(adata.var_names)
adata.var['chromosome']=genes_chr_filtered['chromosome_name']

# %% [markdown]
# Extract X and Y HVGs and compare their number to all expressed X and Y genes.

# %%
# Select X and Y genes that are HVG
x_hvg = adata.var.query('chromosome=="X" & highly_variable').index
y_hvg = adata.var.query('chromosome=="Y" & highly_variable').index
print('X HVG:',len(x_hvg),'/',adata.var.query('chromosome=="X"').shape[0],
      'Y HVG:',len(y_hvg),'/',adata.var.query('chromosome=="Y"').shape[0])

# %% [markdown]
# Show Y gene expression on UMAP.

# %%
# Show Y HVGs and Y non-HVGs
rcParams['figure.figsize']=(3,3)
print('Y specific HVG')
sc.pl.umap(adata, color=y_hvg, size=10, use_raw=False)
print('Y specific non-HVG')
sc.pl.umap(adata, color=adata.var.query('chromosome=="Y"& ~highly_variable').index, size=10, use_raw=False)

# %% [markdown]
# #C: Due to low number of expressed Y genes both HVG and non-HVG genes will be used. Genes Gm47283 (unsepcific??) and Gm29650 (low expression in most cells) will not be used for Y scoring. 
# For X chromosome only HVG will be used. 

# %% [markdown]
# Score cells:

# %%
# Prepare final scoring gene sets for X and Y
y_all=adata.var.query('chromosome=="Y"').index
y_selected=[gene for gene in y_all if gene not in ['Gm47283','Gm29650']]
x_selected=list(x_hvg)
print('N selected genes from Y:',len(y_selected),'and from X:',len(x_selected))

# %%
#Do not use the smaller gene set as controll size as Y gene set is very small
#ctrl_size = min(len(x_genes), len(y_genes))

# For performing it on all batches together
#sc.tl.score_genes(adata, x_selected, score_name = 'x_score', use_raw=False)
#sc.tl.score_genes(adata, y_selected, score_name = 'y_score',use_raw=False)

# Compute sex score per batch
adata.obs['x_score']= np.zeros(adata.shape[0])
adata.obs['y_score'] = np.zeros(adata.shape[0])

for batch in enumerate(adata.obs['file'].cat.categories):
    batch=batch[1]
    idx = adata.obs.query('file=="'+batch+'"').index
    adata_tmp = adata[idx,:].copy()
    sc.tl.score_genes(adata_tmp, x_selected, score_name = 'x_score', use_raw=False)
    sc.tl.score_genes(adata_tmp, y_selected, score_name = 'y_score',use_raw=False)
    adata.obs.loc[idx,'y_score'] = adata_tmp.obs['y_score']
    adata.obs.loc[idx,'x_score'] = adata_tmp.obs['x_score']
    
del adata_tmp

# %% [markdown]
# Plot X and Y scores

# %%
rcParams['figure.figsize']=(10,3)
fig,axs=plt.subplots(1,2)
# Scores across batches
sc.pl.violin(adata, ['x_score'], groupby='file', size=1, log=False,rotation=90,ax=axs[0],show=False)
sc.pl.violin(adata, ['y_score'], groupby='file', size=1, log=False,rotation=90,ax=axs[1],show=False)
plt.show()
# X vs Y score
rcParams['figure.figsize']=(3,3)
sb.scatterplot(x='x_score',y='y_score',data=adata.obs)
# Distribution of scores
sc.pl.umap(adata, color=['x_score','y_score'] ,size=10, use_raw=False)
rcParams['figure.figsize']=(10,3)
fig,axs=plt.subplots(1,2)
sb.distplot(adata.obs['x_score'],  kde=False,  bins=100,ax=axs[0])
sb.distplot(adata.obs['y_score'],  kde=False,  bins=100,ax=axs[1])

# %% [markdown]
# #C: It seems that Y score alone performs much better - X score depends more on the cell type. Thus only Y score will be used for cell type annotation.

# %%
# More detailed plot of y_score region of interest
rcParams['figure.figsize']=(7,3)
sb.distplot(adata.obs.query('y_score>-0.11 & y_score<0.1')['y_score'],  kde=False,  bins=50)

# %% [markdown]
# #C: Set male threshold at >= - 0.07 (Score 0 means equal expression as a reference data set.)

# %%
adata.obs['sex']=(adata.obs['y_score']>=-0.07).replace(False,'female').replace(True,'male')

rcParams['figure.figsize']=(4,4)
sc.pl.umap(adata, color=['sex'] ,size=10, use_raw=False)
print(adata.obs.sex.value_counts())

# %% [markdown]
# ## Save intermediate results before cell type annotation

# %%
if SAVE:
    h.save_h5ad(adata, shared_folder+"data_annotated.h5ad",unique_id2=UID2)

# %% [markdown]
# # Cell type annotation

# %%
adata=h.open_h5ad(shared_folder+"data_annotated.h5ad",unique_id2=UID2)

# %% [markdown]
# ## Endo high annotation

# %%
# Normalise raw data for cell type scoring
adata_rawnorm=adata.raw.to_adata().copy()
adata_rawnorm.X /= adata.obs['size_factors'].values[:,None] # This reshapes the size-factors array
sc.pp.log1p(adata_rawnorm)
adata_rawnorm.X = np.asarray(adata_rawnorm.X)
adata_rawnorm.obs=adata.obs.copy()

# %% [markdown]
# #### Ins

# %%
# Compute Ins score
sc.tl.score_genes(adata_rawnorm, gene_list=['Ins1','Ins2'], score_name='ins_score',  use_raw=False)

# %%
#sc.pl.violin(adata_rawnorm, keys=['ins_score'], groupby='file', stripplot=False, jitter=True)
ins_scores=adata_rawnorm.obs[['ins_score','file']]
ins_scores['ins_score_norm']=pp.minmax_scale(ins_scores.ins_score)
rcParams['figure.figsize']=(12,10)
fig,axs=plt.subplots(2,1)
sb.violinplot(x='file',y='ins_score',data=ins_scores,inner=None,ax=axs[0])
axs[0].title.set_text('Ins scores')
axs[0].grid()
sb.violinplot(x='file',y='ins_score_norm',data=ins_scores,inner=None,ax=axs[1])
axs[1].title.set_text('Scaled Ins scores')
axs[1].grid()
#sb.violinplot(x='file',y='ins_score_norm',data=ins_scores[ins_scores.ins_score_norm>0.2],inner=None,ax=axs[2])
#axs[2].title.set_text('Scaled Ins scores without very low Ins cells')
#axs[2].grid()

# %%
# Find ins high cells
adata_rawnorm.obs['ins_high']=ins_scores.ins_score_norm>0.5
print('Proportion of ins high across samples:')
adata_rawnorm.obs[['file','ins_high']].groupby('file').ins_high.value_counts(normalize=True,sort=False)

# %%
# Add info about ins high to main adata and save it
adata.obs['ins_score']=adata_rawnorm.obs['ins_score']
adata.obs['ins_high']=adata_rawnorm.obs['ins_high']

# %% [markdown]
# #### Gcg

# %%
genes=['Gcg']
score_name='gcg'

# %%
# Compute score
sc.tl.score_genes(adata_rawnorm, gene_list=genes, score_name=score_name+'_score',  use_raw=False)

# %%
scores=adata_rawnorm.obs[[score_name+'_score','file']]
scores[score_name+'_score_norm']=pp.minmax_scale(scores[score_name+'_score'])
rcParams['figure.figsize']=(12,15)
fig,axs=plt.subplots(3,1)
sb.violinplot(x='file',y=score_name+'_score',data=scores,inner=None,ax=axs[0])
axs[0].title.set_text(score_name+' scores')
axs[0].grid()
sb.violinplot(x='file',y=score_name+'_score_norm',data=scores,inner=None,ax=axs[1])
axs[1].title.set_text('Scaled '+score_name+' scores')
axs[1].grid()
sb.violinplot(x='file',y=score_name+'_score_norm',data=scores[scores[score_name+'_score_norm']>0.3],
             inner=None,ax=axs[2])
axs[2].title.set_text('Scaled '+score_name+' scores without very low '+score_name+' cells')
axs[2].grid()

# %%
# Find score high cells
# Use different thresholds across files as there might be different ambient counts (or other effects), 
# thus shifting distributions up a bit
file_thresholds={'MUC13976':0.5, 'MUC13975':0.55, 'MUC13974':0.55}
adata_rawnorm.obs[score_name+'_high']=scores.apply(lambda x: x[score_name+'_score_norm'] > file_thresholds[x.file], 
                                                   axis=1)
print('Proportion of '+score_name+' high across samples:')
adata_rawnorm.obs[['file',score_name+'_high']].groupby('file')[score_name+'_high'].value_counts(
    normalize=True,sort=False)

# %%
# Add info about score high to main adata and save it
adata.obs[score_name+'_score']=adata_rawnorm.obs[score_name+'_score']
adata.obs[score_name+'_high']=adata_rawnorm.obs[score_name+'_high']

# %% [markdown]
# #### Sst

# %%
genes=['Sst']
score_name='sst'

# %%
# Compute score
sc.tl.score_genes(adata_rawnorm, gene_list=genes, score_name=score_name+'_score',  use_raw=False)

# %%
scores=adata_rawnorm.obs[[score_name+'_score','file']]
scores[score_name+'_score_norm']=pp.minmax_scale(scores[score_name+'_score'])
rcParams['figure.figsize']=(12,15)
fig,axs=plt.subplots(3,1)
sb.violinplot(x='file',y=score_name+'_score',data=scores,inner=None,ax=axs[0])
axs[0].title.set_text(score_name+' scores')
axs[0].grid()
sb.violinplot(x='file',y=score_name+'_score_norm',data=scores,inner=None,ax=axs[1])
axs[1].title.set_text('Scaled '+score_name+' scores')
axs[1].grid()
sb.violinplot(x='file',y=score_name+'_score_norm',data=scores[scores[score_name+'_score_norm']>0.2],
             inner=None,ax=axs[2])
axs[2].title.set_text('Scaled '+score_name+' scores without very low '+score_name+' cells')
axs[2].grid()

# %%
# Find score high cells
# Use different thresholds across files as there might be different ambient counts (or other effects), 
# thus shifting distributions up a bit
file_thresholds={'MUC13976':0.55, 'MUC13975':0.55, 'MUC13974':0.6}
adata_rawnorm.obs[score_name+'_high']=scores.apply(lambda x: x[score_name+'_score_norm'] > file_thresholds[x.file], 
                                                   axis=1)
print('Proportion of '+score_name+' high across samples:')
adata_rawnorm.obs[['file',score_name+'_high']].groupby('file')[score_name+'_high'].value_counts(
    normalize=True,sort=False)

# %%
# Add info about score high to main adata and save it
adata.obs[score_name+'_score']=adata_rawnorm.obs[score_name+'_score']
adata.obs[score_name+'_high']=adata_rawnorm.obs[score_name+'_high']

# %%
#### Ppy

# %%
genes=['Ppy']
score_name='ppy'

# %%
# Compute score
sc.tl.score_genes(adata_rawnorm, gene_list=genes, score_name=score_name+'_score',  use_raw=False)

# %%
scores=adata_rawnorm.obs[[score_name+'_score','file']]
scores[score_name+'_score_norm']=pp.minmax_scale(scores[score_name+'_score'])
rcParams['figure.figsize']=(12,15)
fig,axs=plt.subplots(3,1)
sb.violinplot(x='file',y=score_name+'_score',data=scores,inner=None,ax=axs[0])
axs[0].title.set_text(score_name+' scores')
axs[0].grid()
sb.violinplot(x='file',y=score_name+'_score_norm',data=scores,inner=None,ax=axs[1])
axs[1].title.set_text('Scaled '+score_name+' scores')
axs[1].grid()
sb.violinplot(x='file',y=score_name+'_score_norm',data=scores[scores[score_name+'_score_norm']>0.55],
             inner=None,ax=axs[2])
axs[2].title.set_text('Scaled '+score_name+' scores without very low '+score_name+' cells')
axs[2].grid()

# %%
# Find score high cells
# Use different thresholds across files as there might be different ambient counts (or other effects), 
# thus shifting distributions up a bit
file_thresholds={'MUC13976':0.83, 'MUC13975':0.83, 'MUC13974':0.8}
adata_rawnorm.obs[score_name+'_high']=scores.apply(lambda x: x[score_name+'_score_norm'] > file_thresholds[x.file], 
                                                   axis=1)
print('Proportion of '+score_name+' high across samples:')
adata_rawnorm.obs[['file',score_name+'_high']].groupby('file')[score_name+'_high'].value_counts(
    normalize=True,sort=False)

# %%
# Add info about score high to main adata and save it
adata.obs[score_name+'_score']=adata_rawnorm.obs[score_name+'_score']
adata.obs[score_name+'_high']=adata_rawnorm.obs[score_name+'_high']

# %% [markdown]
# #### Save

# %%
if SAVE:
    h.save_h5ad(adata, shared_folder+"data_annotated.h5ad",unique_id2=UID2)

# %% [markdown]
# ## Clustering

# %% [markdown]
# #### Leiden clustering on log transformed data.

# %%
sc.tl.leiden(adata,resolution=0.4)

# %%
rcParams['figure.figsize']=(6,6)
sc.pl.umap(adata, color=['leiden'] ,size=10, use_raw=False)

# %% [markdown]
# #### Seurat style clustering

# %% [raw]
# # Preapre data for Seurat clustering
# expression=pd.DataFrame(adata.X.T,index=adata.var_names,columns=adata.obs.index)
# hvg=adata.var_names[adata.var.highly_variable]

# %% [raw] magic_args="-i expression -i hvg -i N_PCS -i shared_folder" language="R"
# # Seurat clustering data preparatrion - so that seurat object required for clustering can be computed once and then reused
# seurat_obj<-CreateSeuratObject(counts=expression)
# seurat_obj <- ScaleData(seurat_obj, features = hvg)
# seurat_obj <- RunPCA(seurat_obj, features = hvg,npcs=N_PCS)
# seurat_obj <- FindNeighbors(seurat_obj, dims = 1:N_PCS)
# saveRDS(seurat_obj, file = paste0(shared_folder,"data_clustering_seurat_annotemp.rds"))

# %% [raw]
# res=0.3

# %% [raw] magic_args="-i res -i shared_folder -o clusters " language="R"
# #Seurat clustering
# seurat_obj <- readRDS( file = paste0(shared_folder,"data_clustering_seurat_annotemp.rds"))
# seurat_obj <- FindClusters(seurat_obj, resolution = res)
# clusters<-data.frame(unlist(Idents(seurat_obj )))
# rownames(clusters)<-names(Idents(seurat_obj ))
# colnames(clusters)<-c('cluster_seurat')

# %% [raw]
# # Add Seurat clusters
# clusters=clusters.reindex(adata.obs.index)
# adata.obs['cluster_seurat_r'+str(res)]=clusters.cluster_seurat

# %% [raw]
# # Plot Seurat clustering
# rcParams['figure.figsize']=(6,6)
# sc.pl.umap(adata, color=['cluster_seurat_r0.3'] ,size=10, use_raw=False)

# %% [markdown]
# #### Leiden clustering on log transformed z-scaled data.

# %%
# Scale data and perform PCA
adata_scl=adata.copy()
sc.pp.scale(adata_scl,max_value=10)
sc.pp.pca(adata_scl, n_comps=30, use_highly_variable=True, svd_solver='arpack')
sc.pl.pca_variance_ratio(adata_scl)

# %%
#C: Can stay the same as above
N_PCS

# %%
# neighbours on scaled data
sc.pp.neighbors(adata_scl,n_pcs = N_PCS) 

# %%
# This neighbour weight computation (used in  Seurat) does not improve clustering - the main improvement is due to scaling
#snn.shared_knn_adata(adata,n_pcs=N_PCS,n_jobs=8)

# %%
# Umap on scaled data
sc.tl.umap(adata_scl)

# %%
# Add scaled embedding to adata
adata.obsm['X_umap_scl']=adata_scl.obsm['X_umap']

# %%
#del adata_scl.uns['sex_colors']
rcParams['figure.figsize']=(6,6)
sc.pl.umap(adata_scl, color=['sex','file','phase_cyclone'] ,size=10, use_raw=False,wspace=0.3)

# %%
# Clustering resolution
res=0.4

# %%
# Cluster scaled data
sc.tl.leiden(adata_scl, resolution=res, key_added='leiden_scaled_r'+str(res), directed=True, use_weights=True)

# %%
# Compare UMAPs and clusters on scaled data
rcParams['figure.figsize']=(6,6)
sc.pl.umap(adata_scl, color=['leiden_scaled_r'+str(res)] ,size=10, use_raw=False)

# %%
sc.pl.umap(adata_scl, color=['pre_cell_type'] ,size=10, use_raw=False)

# %% [markdown]
# #C: Umaps and clusterings on z-scaled data and non-z-scaled data perform similarly. z-scaled data will be used for consistency with other analysed studies.

# %% [markdown]
# ## Cell type annotation

# %%
# Normalise raw data for plotting and cell type scoring
adata_raw=adata_scl.raw.to_adata().copy()
sc.pp.normalize_total(adata_raw, target_sum=1e4, exclude_highly_expressed=True,inplace=False)
sc.pp.log1p(adata_raw)
adata_rawnormalised=adata_scl.copy()
adata_rawnormalised.raw=adata_raw
del adata_raw

# %%
# Markers data
markers=pd.read_excel('/lustre/groups/ml01/workspace/karin.hrovatin/data/pancreas/gene_lists/markers.xlsx',
                          sheet_name='mice')

# %%
# Subset markers to non-immature and non-dedifferentiated for initial annotation
print('Subtypes (original):',markers.Subtype.unique())
remove_subtype=['immature','dedifferentiated']
remove_subtype=[]
markers_filter=markers.query('Subtype not in @remove_subtype')

# %%
# Plot markers for each cell type
# Plot markers for each cell type
for cell_type in sorted(list(markers_filter.Cell.unique()), key=str.lower):
    print(cell_type)
    genes=list(markers_filter.query('Cell == "'+cell_type+'"').Gene)
    # Retain genes present in raw var_names
    missing=[gene for gene in genes if gene not in adata.raw.var_names]
    genes=[gene for gene in genes if gene in adata.raw.var_names]
    if len(genes)>0:
        print('Missing genes:',missing)
        rcParams['figure.figsize']=(4,4)
        sc.pl.umap(adata_rawnormalised, color=['pre_cell_type'],size=10, use_raw=True)
        sc.pl.umap(adata_rawnormalised, color=genes ,size=10, use_raw=True)
    else:
        print('No availiable genes (out of:',missing,')\n')

# %%
# Selected markers that seem to be able to distinguish between cell types
# Use only hormone genes for endocrine cells
markers_selection={
'immune':['Cd86','Cd74','Ptprc','Cd52','Lyz2'],
'schwann':['Cmtm5','Ngfr','Plp1'],
'stellate':['Col1a2','Pdgfra'],
'endothelial':['Plvap','Pecam1'],
'pericyte':['Ndufa4l2','Pdgfrb','Acta2','Cspg4','Des','Rgs5','Abcc9'],
'acinar':['Cpa1','Prss2'],
'ductal':['Muc1','Sox9','Anxa2','Bicc1','Spp1','Krt19'],
'alpha':['Gcg'],
'beta':['Ins1','Ins2'],
'delta':['Sst'],
'gamma':['Ppy'],
'epsilon':['Ghrl']
}

#markers_selection={
#'immune':['Cd74','Ptprc','Cd86','Adgre1','Lyz2','Cd86','Itgax','Cd52'],
#'schwann':['Sox10'],
#'stellate':['Col1a2','Pdgfra'],
#'endothelial':['Plvap','Pecam1'],
#'ductal':['Muc1','Sox9','Spp1','Krt19'],
#'acinar':['Cpa1','Prss2'],
#'beta':['Slc2a2','Ins1','Ins2'],
#'alpha':['Gcg','Irx1','Irx2'],
#'delta':['Sst','Hhex','Neurog3'],
#'gamma':['Ppy'],
#'epsilon':['Ghrl']
#}

# %% [markdown]
# ### Marker expression scores
# Score each cell for marker expression of each cell type. Cells can thus be annotated qith 0 to N cell types. The presence of annotations is then checked for each cluster.

# %%
#Score cells for each cell type

# Save score column names 
scores=[]
for cell_type,genes in markers_selection.items():
    score_name=cell_type+'_score'
    scores.append(cell_type+'_score')
    sc.tl.score_genes(adata_rawnormalised, gene_list=genes, score_name=score_name,  use_raw=True)

# %%
# Which clusters (column name) to analyse for cell scores
res=0.4
clusters_col='leiden_scaled_r'+str(res)

# %%
# Add cluster information to the used adata
adata_rawnormalised.obs[clusters_col]=adata_scl.obs[clusters_col]

# %%
# Plot scores distribution across clusters
rcParams['figure.figsize']=(10,3)
for score in scores:
    sc.pl.violin(adata_rawnormalised, keys=score, groupby=clusters_col, use_raw=True, stripplot=False)

# %%
# Scores per cluster, scaled from 0 to 1 in each cell type
#C: Not very informative!
#scores_df=adata_rawnormalised.obs[scores+[clusters_col]]
#score_means=scores_df.groupby(clusters_col).mean()
#score_means=pd.DataFrame(pp.minmax_scale(score_means),index=score_means.index,columns=score_means.columns)
#sb.clustermap(score_means,yticklabels=1)

# %%
# Scores normalised to interval [0,1] for each cell type - so that they can be more easily compared
scores_df_norm=adata_rawnormalised.obs[scores]
scores_df_norm=pd.DataFrame(pp.minmax_scale(scores_df_norm),columns=scores_df_norm.columns,index=adata_rawnormalised.obs.index)

# %%
# Plot of normalised scores distribution in whole dataset, per cluster
rcParams['figure.figsize']=(20,3)
fig,ax=plt.subplots()
sb.violinplot(data=scores_df_norm,inner=None,ax=ax)
ax.grid()

# %%
# Plot of normalised scores distribution, excluding low scores, per cluster
rcParams['figure.figsize']=(20,3)
fig,ax=plt.subplots()
sb.violinplot(data=scores_df_norm[scores_df_norm>0.1],inner=None,ax=ax)
ax.grid()

# %%
# Check gamma score in gamma cluster to reset the threshold
# Cluster 5 contains only partialy gamma cells
fig,ax1=plt.subplots()
a=ax1.hist(scores_df_norm.gamma_score[(adata_scl.obs[clusters_col]=='5').values],bins=80,alpha=0.5,color='r')
ax1.tick_params(axis='y', labelcolor='r')
ax2 = ax1.twinx()
a=ax2.hist(scores_df_norm.gamma_score[(adata_scl.obs[clusters_col]!='5').values],bins=80,alpha=0.5,color='b')
ax2.tick_params(axis='y', labelcolor='b')

# %%
# Thresholds for cell type assignemnt based on normalised scores
thresholds=[]
for col in scores_df_norm:
    threshold=0.4
    if col=='gamma_score':
        threshold=0.83
    elif col=='schwann_score':
        threshold=0.7
    elif col=='stellate_score':
        threshold=0.5
    elif col=='beta_score':
        threshold=0.5
    elif col =='alpha_score' :
        threshold=0.6
    elif col =='delta_score' :
        threshold=0.6
    thresholds.append(threshold)


# %%
# Assign cell types based on scores to each cell
assignment_df=scores_df_norm>=thresholds
assignment_df.columns=[col.replace('_score','') for col in scores_df_norm.columns] 

# %%
# Count of cells per cell type
assignment_df[[col.replace('_score','') for col in scores_df_norm.columns]].sum()

# %% [markdown]
# #C: Epsilon cells will be dissregarded as there are so few (2).

# %%
# How many cell types were annotated to each cell
a=plt.hist(assignment_df.sum(axis=1))

# %%
# For each cell make a (standard) string of annotated cell types: 
# e.g. each annotated cell type in the same order, separated by '_' when multiple cell types were annotated
type_unions=[]
for idx,row in assignment_df.iterrows():
    type_union=''
    for col in row.index:
        if row[col]:
            type_union=type_union+col+'_'
    if type_union=='':
        type_union='NA'
    type_unions.append(type_union.rstrip('_'))

# %%
# Add cell types strings of cells to scores/assignment DF
assignment_df['type_union']=type_unions
assignment_df[clusters_col]=adata_rawnormalised.obs[clusters_col].values

# %% [markdown]
# ### Annotate clusters

# %%
# Make DF of marker gene expressions (normalised, log transformed), scaled for each gene to [0,1]
used_markers=list(dict.fromkeys([marker for marker_list in markers_selection.values() for marker in marker_list]))
gene_idx=adata_rawnormalised.raw.var_names.isin(used_markers)
genes=adata_rawnormalised.raw.var_names[gene_idx]
scaled_expression=pd.DataFrame(pp.minmax_scale(adata_rawnormalised.raw.X.toarray()[:, gene_idx]),
                               columns=genes,index=adata_rawnormalised.obs.index
                              )[[marker for marker in used_markers if marker in genes]]


# %%
def add_category(df,idxs,col,category):
    """
    Add single value to multiple rows of DF column (useful when column might be categorical). 
    If column is categorical the value is beforehand added in the list of present categories 
    (required for categorical columns). 
    :param df: DF to which to add values
    :param idxs: Index names of rows where the value should be assigned to the column.
    :param col: Column to which to add the value.
    :param category: The value to add to rows,column.
    """
    # If column is already present, is categorical and value is not in categories add the value to categories first.
    if col in df.columns and df[col].dtype.name=='category' and category not in df[col].cat.categories:
        df[col] = df[col].cat.add_categories([category])
    df.loc[idxs,col]=category


# %%
def subcluster(adata_cluster,res,original_cluster,assignment_df_temp,clusters_name_prefix='leiden_scaled_r'):
    """
    Cluster adata and add reult into cell type assignment DF. Plot the clustering on UMAP.
    Add name of the original cluster to which the adata belongs to new cluster names.
    Cluster column name: clusters_name_prefix+str(res) 
    :param adata_cluster: Adata (with already computed neighbours and UMAP) to cluster with leiden clustering. 
    :param res: Leiden resolution
    :param original_cluster: Original cluster name, new clusters are named 'original cluster'+'_'+'new cluster'
    :param assignment_df_temp: assignment_df to which to add clusters - should have same row order as adata
    :param clusters_name_prefix: Prefix for cluster column name.
    """
    clusters_col_name=clusters_name_prefix+str(res)
    sc.tl.leiden(adata_cluster, resolution=res, key_added=clusters_col_name, directed=True, use_weights=True)
    adata_cluster.obs[clusters_col_name]=[original_cluster+'_'+subcluster 
                                                 for subcluster in adata_cluster.obs[clusters_col_name]]
    sc.pl.umap(adata_cluster,color=clusters_col_name)
    time.sleep(1.0)
    
    assignment_df_temp['leiden_scaled_r'+str(res)]=adata_cluster.obs['leiden_scaled_r'+str(res)].values
    
def get_cluster_data(adata_original, cluster,cluster_col,assignment_df):
    """
    Subset adata and assignment_df to cluster.
    :param adata_original: Adata to subset.
    :param  cluster: Cluster for which to extract the data.
    :param cluster_col: Column where clusters are listed. Should be present in adata and assignment_df.
    :param assignment_df: DF with cell type assignmnets in column 'type_union' and cluster info. Should have index names
    that are present in adata.obs.index.
    :return: Subset of adata, assignment_df
    """
    adata_temp=adata_original[adata_original.obs[cluster_col]==cluster].copy()
    assignment_df_temp=pd.DataFrame(assignment_df.loc[adata_temp.obs.index,'type_union'])
    return adata_temp, assignment_df_temp

def cluster_annotate(assignment_df,cluster_col,present_threshold,nomain_threshold,
                     save,cluster_annotation,adata_main):
    """
    Loop through clusters, check present cell types and if there is no main cell type plot expression and QC metrics.
    For each cluster list proportion of present cell types.
    Expression (normalised, log transformed, [0,1] per gene scaled) is plotted for marker genes across cells (heatmap).
    QC metrics are plotted as scatterplot of N genes and N counts with cluster cells overlayed over all cels.
    :param assignment_df: DF with cell type assignment in column 'type_union' and cluster assignment.
    :param cluster_col: Cluster column name in assignment_df.
    :param present_threshold: Count among present cell types each cell type present if it represents 
    at least present_threshold proportion of cells in cluster. 
    :param nomain_threshold: If only 1 cell type was selected with present_threshold and 
    no cell type is present at proportion at least nomain_threshold add 'other' to annotated cell types list.
    :param save: Save cluster information to adata_main (column 'cluster') and cell types list to cluster_annotation.
    :param cluster_annotation: Dict where each cluster (key) has list of annotated cell types (value).
    :param adata_main: Add cluster to adata_main.obs.cluster. Use this adata for plotting of QC mettrics (for this a
    column 'temp_selected' is added.)
    """
    for group in assignment_df[['type_union',cluster_col]].groupby(cluster_col):
        types_summary=group[1].type_union.value_counts(normalize=True)
        present=list(types_summary[types_summary >= present_threshold].index)
        if len(present)==1 and types_summary.max() < nomain_threshold:
            present.append('other')
            
        if save:
            cluster_annotation[group[0]]=present
            add_category(df=adata_main.obs,idxs=group[1].index,col='cluster',category=group[0])
        
        print('\nCluster:',group[0],'\tsize:',group[1].shape[0])    
        print('Present:',present)
        print(types_summary)
        
        #present_nonna=[cell_type for cell_type in present if cell_type !='NA']
        #if len(present_nonna)!=1:
        if len(present)!=1 or present==['NA']:
            sb.clustermap(
                pd.DataFrame(scaled_expression.loc[group[1].index,:]),
                col_cluster=False,xticklabels=1,yticklabels=False,figsize=(7,5),vmin=0,vmax=1)
            plt.title('Cluster: '+group[0]+' assigned:'+str(present))
            adata_main.obs['temp_selected']=adata_main.obs.index.isin(group[1].index)
            rcParams['figure.figsize']=(5,5)
            p1 = sc.pl.scatter(adata_main, 'n_counts', 'n_genes', color='temp_selected', size=40,color_map='viridis')
            time.sleep(1.0)

def save_cluster_annotation(adata,cluster_name,cell_types:list,cell_names):
    """
    Save cluster information for a set of cells to cluster_annotation (from outer scope) dictionary and specified adata.
    :param adata: Adata to which to save cluster name for cells. 
    Cluster information is saved to adata.obs in 'cluster' column.
    :param cluster_name: Name of the cluster.
    :param cell_types: List of cell types annotated to the cluster.
    :param cell_names: Cell names (matching adata.obs.index) to which the new cluster is asigned.
    """
    cluster_annotation[cluster_name]=cell_types
    add_category(df=adata.obs,idxs=cell_names,col='cluster',category=cluster_name)


# %%
#Save cell types annotated to each cluster
cluster_annotation=dict()

# %%
# Display cell type annotation distribution of each cluster.
cluster_annotate(assignment_df=assignment_df,
                 cluster_col=clusters_col,present_threshold=0.1,nomain_threshold=0.7,
                     save=True,cluster_annotation=cluster_annotation,adata_main=adata_rawnormalised)

# %%
# Correct annotation
cluster_annotation['8']=['immune']
#cluster_annotation['11']=['acinar']

# %%
# recluster clusters that previously had less or more than 1 annotted cell type (exclusing NA and other).
for cluster in sorted(list(adata_rawnormalised.obs['cluster'].unique()),key=int):
    if len(cluster_annotation[cluster]) != 1 or len(
        [cell_type for cell_type in cluster_annotation[cluster] if cell_type !='NA' and cell_type !='other']) == 0:
        print('**** Original cluster',cluster)
        res=0.3
        adata_temp,assignment_df_temp=get_cluster_data(adata_original=adata_rawnormalised, cluster=cluster,
                                                       cluster_col='cluster',assignment_df=assignment_df)
        subcluster(adata_cluster=adata_temp,res=res,original_cluster=cluster,assignment_df_temp=assignment_df_temp)
        cluster_annotate(assignment_df=assignment_df_temp,
                         cluster_col='leiden_scaled_r'+str(res),
                         # Use more leanient condition as this is already subclustered - 
                        # otherwise data could be in some cases subclustered almost idefinitely
                         present_threshold=0.1,nomain_threshold=0.9,
                     save=True,cluster_annotation=cluster_annotation,adata_main= adata_rawnormalised)

# %%
# Expression of markers in cluster 11_3
sb.clustermap(pd.DataFrame(scaled_expression.loc[adata_rawnormalised.obs.query('cluster=="11_3"').index,:]), 
                  row_cluster=True, col_cluster=False,xticklabels=1,yticklabels=False,figsize=(7,5),vmin=0,vmax=1)

# %%
# Correct entries in cluster_annotation dict - all clusters that do not have exactly one entry will be assigned 'NA'
# If cluster is to be removed add 'remove'

cluster_annotation['6_2']=['beta_delta']
cluster_annotation['7_2']=['endothelial_pericyte']
cluster_annotation['7_4']=['endothelial']
cluster_annotation['9_3']=['pericyte']
cluster_annotation['11_0']=['acinar']
cluster_annotation['11_1']=['acinar']
cluster_annotation['11_2']=['acinar']
cluster_annotation['11_3']=['acinar_low']

# %%
for cluster in sorted(list(adata_rawnormalised.obs['cluster'].unique()),key=int):
    if len(cluster_annotation[cluster]) != 1 or len(
        [cell_type for cell_type in cluster_annotation[cluster] if cell_type !='NA' and cell_type !='other']) == 0:
        print('**** Original cluster',cluster)
        res=0.5
        adata_temp,assignment_df_temp=get_cluster_data(adata_original=adata_rawnormalised, cluster=cluster,
                                                       cluster_col='cluster',assignment_df=assignment_df)
        subcluster(adata_cluster=adata_temp,res=res,original_cluster=cluster,assignment_df_temp=assignment_df_temp)
        cluster_annotate(assignment_df=assignment_df_temp,
                         cluster_col='leiden_scaled_r'+str(res),
                         # Use more leanient condition as this is already subclustered - 
                        # otherwise data could be in some cases subclustered almost idefinitely
                         present_threshold=0.2,nomain_threshold=0.8,
                     save=False,cluster_annotation=cluster_annotation,adata_main= adata_rawnormalised)

# %% [markdown]
# #C: The above clustering could not resolve most clusters. However, it did resolve 9_1 and 9_2 to some extent thus those subclusters will be further subclustered.

# %%
for cluster in ['9_1','9_2']:
    if len(cluster_annotation[cluster]) != 1 or len(
        [cell_type for cell_type in cluster_annotation[cluster] if cell_type !='NA' and cell_type !='other']) == 0:
        print('**** Original cluster',cluster)
        res=0.8
        adata_temp,assignment_df_temp=get_cluster_data(adata_original=adata_rawnormalised, cluster=cluster,
                                                       cluster_col='cluster',assignment_df=assignment_df)
        subcluster(adata_cluster=adata_temp,res=res,original_cluster=cluster,assignment_df_temp=assignment_df_temp)
        cluster_annotate(assignment_df=assignment_df_temp,
                         cluster_col='leiden_scaled_r'+str(res),
                         # Use more leanient condition as this is already subclustered - 
                        # otherwise data could be in some cases subclustered almost idefinitely
                         present_threshold=0.2,nomain_threshold=0.8,
                     save=True,cluster_annotation=cluster_annotation,adata_main= adata_rawnormalised)

# %%
cluster_annotation['9_1_0']=['schwann']
cluster_annotation['9_1_1']=['schwann']
cluster_annotation['9_1_2']=['NA']
cluster_annotation['9_2_0']=['stellate']
cluster_annotation['9_2_1']=['pericyte']

# %% [markdown]
# #### Annotate cells from unsolvable clusters based on cell type score threshold
# All those clusters are endocrine so strip any non-endocrine annotations from cell names.

# %%
# Get clusters that still do not have single cell type annotation
unsolvable=[]
for cluster in sorted(list(adata_rawnormalised.obs['cluster'].unique()),key=int):
    if len(cluster_annotation[cluster]) != 1:
        unsolvable.append(cluster)
print('Unsolvable clusters:',unsolvable)        

# %%
# Get all cells from the clusters 
idx_unsolvable=adata_rawnormalised.obs.query('cluster in @unsolvable').index

# %% [markdown]
# Do not use epsilon cells as there were only 2 - unreliable.

# %%
# Make new assignments with only endocrine cell types (excluding epsilone)
type_unions=[]
for idx in idx_unsolvable:
    row=assignment_df.loc[idx,:]
    type_union=''
    # Use list comprehension instead of just the endocrine list so that names of cell types stay in the same order as above
    for col in [col for col in row.index if col in ['alpha','beta','delta','gamma']]:
        if row[col]:
            type_union=type_union+col+'_'
    if type_union=='':
        type_union='NA'
    type_unions.append(type_union.rstrip('_'))

#Reasign cell types in assignment_df
assignment_df.loc[idx_unsolvable,'type_union']=type_unions

# %%
# Group unsolvable cells by cell type and plot expression to check if assignment was ok
for cell_type in assignment_df.loc[idx_unsolvable,'type_union'].unique():
    type_idx=assignment_df.loc[idx_unsolvable,:].query('type_union == "'+cell_type+'"').index
    print(cell_type,'N:',len(type_idx))
    row_cluster=True
    if len(type_idx)<2:
        row_cluster=False
    sb.clustermap(pd.DataFrame(scaled_expression.loc[type_idx,:]), 
                  row_cluster=row_cluster, col_cluster=False,xticklabels=1,yticklabels=False,figsize=(7,5),vmin=0,vmax=1)
    plt.show()
    time.sleep(1.0)

# %%
# Replace cluster names in adata and cluster_annotation with threshold based annotation
for cell_type in assignment_df.loc[idx_unsolvable,'type_union'].unique():
    # Subset assignment_df to idx_unsolvable before extracting idices of each cell type so that 
    # Cells from other clusters to not get assigned new clusters because they share phenotype
    type_idx=assignment_df.loc[idx_unsolvable,:].query('type_union == "'+cell_type+'"').index
    save_cluster_annotation(adata=adata_rawnormalised,cluster_name=cell_type,cell_types=[cell_type],cell_names=type_idx)

# %% [markdown]
# #### Add cluster based annotation to adata

# %%
# Display cluster annotation of clusters that will be used
clusters=list(adata_rawnormalised.obs['cluster'].unique())
clusters.sort()
for cluster in clusters:
    print(cluster ,cluster_annotation[cluster ])

# %%
# Add cell type annotation to clusters. 
# If clusters was annotated with more than one cell type (inbcluding NA or other) set it to 'NA'.
if 'cell_type' in adata_rawnormalised.obs.columns:
    adata_rawnormalised.obs.drop('cell_type',axis=1,inplace=True)
for row_idx in adata_rawnormalised.obs.index:
    cluster=adata_rawnormalised.obs.at[row_idx,'cluster']
    cell_type=cluster_annotation[cluster]
    if len(cell_type)!=1:
        cell_type='NA'
    else:
        cell_type=cell_type[0]
        
    add_category(df=adata_rawnormalised.obs,idxs=row_idx,col='cell_type',category=cell_type)


# %% [markdown]
# ### Cell type annotation evaluation

# %%
# Plot cell types on UMPA (pre-annotated and new ones)
rcParams['figure.figsize']=(6,6)
sc.pl.umap(adata_rawnormalised, color=['pre_cell_type','cell_type'], size=40, use_raw=False,wspace=0.3)

# %%
# Count of new cell types
adata_rawnormalised.obs.cell_type.value_counts()

# %%
# Plot mean marker expression in each cluster
rcParams['figure.figsize']=(10,5)
fig,ax=plt.subplots()
sb.heatmap(scaled_expression.groupby(adata_rawnormalised.obs['pre_cell_type']).mean(),yticklabels=1,xticklabels=1,
          vmin=0,vmax=1)
ax.set_title('pre_cell_type')
fig,ax=plt.subplots()
sb.heatmap(scaled_expression.groupby(adata_rawnormalised.obs['cell_type']).mean(),yticklabels=1,xticklabels=1,
          vmin=0,vmax=1)
ax.set_title('cell_type')

# %% [markdown]
# Expression of markers in individual NA cells.

# %%
# Subset marker expression to NA cell type cells and plot heatmap
sb.clustermap(pd.DataFrame(scaled_expression[adata_rawnormalised.obs.cell_type=='NA']), 
                  row_cluster=True, col_cluster=False,xticklabels=1,yticklabels=False,figsize=(7,5))

# %%
# Add cell type to adata
adata.obs['cell_type']=adata_rawnormalised.obs.cell_type
# Add final clusters and starting clusters to adata
adata.obs[['cluster',clusters_col]]=adata_rawnormalised.obs[['cluster',clusters_col]]
# Add cell type scores
score_cols=[col for col in scores_df_norm.columns if '_score' in col]
adata.obs[score_cols]=scores_df_norm[score_cols].reindex(adata.obs.index)

# %% [markdown]
# QC metrics in each cell type.

# %%
# QC metrics per cell type
rcParams['figure.figsize']=(10,3)
sc.pl.violin(adata, ['n_counts'], groupby='cell_type', size=1, log=True,rotation=90)
sc.pl.violin(adata, ['n_genes'], groupby='cell_type', size=1, log=False,rotation=90)
sc.pl.violin(adata, ['mt_frac'], groupby='cell_type', size=1, log=False,rotation=90)
sc.pl.violin(adata, 'doublet_score',groupby='cell_type',size=1, log=True,rotation=90)


# %% [markdown]
# #C: The double cell type populations might be doublets.

# %% [markdown]
# Add celly type data to original adata for saving.

# %% [markdown]
# #### Cell type markers

# %% [markdown]
# Upregulated genes in each cell type compared to other cells on normalised log scaled data.

# %%
# Compute overexpressed genes in each cell type on normalised log scaled data
#Retain only cell types with >=10 cells and non-NA annotation
groups_counts=adata.obs.cell_type.value_counts()
groups=[cell_type for cell_type in groups_counts[groups_counts>=10].index if cell_type!='NA']
# Compute markers
sc.tl.rank_genes_groups(adata,groupby='cell_type',groups=groups, use_raw=False)
sc.tl.filter_rank_genes_groups(adata,groupby='cell_type', use_raw=False)

# %%
# Plot cell_type vs rest upregulated genes
rcParams['figure.figsize']=(4,3)
sc.pl.rank_genes_groups(adata,key='rank_genes_groups_filtered')

# %% [markdown]
# Expression of upregulated genes on normalised log transformed z-scaled data

# %%
# Plot expression of cell type upregulated genes on normalised log transformed z-scaled data
adata_scl.uns['rank_genes_groups_filtered']=adata.uns['rank_genes_groups_filtered']
adata_scl.obs['cell_type']=adata.obs['cell_type']
sc.pl.rank_genes_groups_stacked_violin(adata_scl,key='rank_genes_groups_filtered',n_genes=3,use_raw=False)

# %% [markdown]
# ### Expected doublet rates
#
# Adapted from https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6126471/#ref-7, but using 0.1 as doublet rate (described in my notes).
#
# Expected multiplet number is calculated for each file separately.

# %%
# Singlet cell types whose multiplet rates are predicted
cell_types=['alpha','beta','gamma','delta']
# DFs with expected multiplet rates
expected_dfs=[]
# Calculate expected rate for each file separately
for file in adata.obs.file.unique():
    print('\nFile:',file)
    cell_type_temp=adata.obs.query('file == "'+file+'"').cell_type.copy()
    
    # N of droplets containing at least one cell of the relevant cell type
    Ns=dict()
    for cell_type in cell_types:
        n_celltype=cell_type_temp.str.contains(cell_type).sum()
        Ns[cell_type]=n_celltype
    print('N droplets that contain at least one:',Ns)
    
    # Calculate N (see formula in notes)
    N=emr.get_N(Ns=Ns.values())
    regex_any='|'.join(['.*'+cell_type+'.*' for cell_type in cell_types])
    print('N:',round(N,1), '(observed cell-containing N with relevant cell types:',
          cell_type_temp.str.contains(fr'{regex_any}').sum(),')')
    
    # Calculate mu for each cell type
    mus=dict()
    for cell_type in cell_types:
        mus[cell_type]=emr.mu_cell_type(N_cell_type=Ns[cell_type], N=N)
    print('mu:',{k:round(v,4) for k,v in mus.items()})
    
    # Extract multiplet types and their components
    multiplet_types=dict()
    for cell_type in cell_type_temp.unique():
        # Get components of multiplets by retaining name parts contained in original cell type dict
        components_all=cell_type.split('_')
        components_relevant=[type_singlet for type_singlet in components_all if type_singlet in cell_types]
        if len(components_relevant) > 1:
            multiplet_types[cell_type]=components_relevant
            # This does not assure that initially the cell types are not counted wrongly 
            # (e.g. including proliferative, ...)
            #if len(components_relevant) < len(components_all):
            #    warnings.warn('Multiplet type has additional unrecognised component: '+cell_type)
    #print('Relevant multiplet cell types:',multiplet_types.keys())
    
    # This also analyses O and E of singlet types, but this is not so relevant as changes in multiplets also 
    # affect it?
    #types_OE= dict(zip(cell_types,[[i] for i in cell_types]))
    #types_OE.update(multiplet_types)
    
    # Calculate O (observed) and E (expected) numbers
    expected_df=pd.DataFrame(index=multiplet_types.keys(),columns=['O_'+file,'E_'+file
                                                                  # ,'E_atleast'
                                                                  ])
    #for multiplet, components in types_OE.items():
    for multiplet, components in multiplet_types.items():
        absent=np.setdiff1d(cell_types,components)
        # N of cellls of this cell type
        expected_df.at[multiplet,'O_'+file]=(cell_type_temp==multiplet).sum()
        # Expected N of cells that have all the individual cell types of multiplet and non of the other 
        # considered possible multiplet ontributors
        expected_df.at[multiplet,'E_'+file]=emr.expected_multiplet(
            mu_present=[mus[cell_type] for cell_type in components], 
            mu_absent=[mus[cell_type] for cell_type in absent], 
            N=N)
        # E that droplet contains at least one cell of each present cell type,
        # but does not exclude other cell types from being present
        #expected_df.at[multiplet,'E_atleast']=emr.expected_multiplet(
        #    mu_present=[mus[cell_type] for cell_type in components], 
        #    mu_absent=[], 
        #    N=N)
    expected_dfs.append(expected_df)
    
# Merge O/E rates for all files into single DF
display(pd.concat(expected_dfs,axis=1))
del cell_type_temp

# %% [markdown]
# #C: Despite alpha_beta_delta having O > E it will be treated as multiplet, as this cell type was multiplet like in other studies (Fltp, STZ ref, VSG ref) and it does not have very large cell numbers. The cells are also very dispersed on UMAP.

# %%
# Reassign cell types to multiplet
multiplets=['beta_delta','alpha_beta','alpha_beta_gamma','beta_gamma',
            'beta_delta_gamma','alpha_beta_delta_gamma','alpha_beta_delta']
adata.obs['cell_type_multiplet']=adata.obs.cell_type.replace(multiplets, 'multiplet')

# %%
# Plot new cell types
rcParams['figure.figsize']=(6,6)
sc.pl.embedding(adata,'X_umap_scl', color=['cell_type','cell_type_multiplet'], size=40, use_raw=False,wspace=0.7)

# %% [markdown]
# ## Resolve beta subtypes

# %% [markdown]
# #### Preprocess beta cell data

# %% [markdown]
# Select beta cells only

# %%
[ct for ct in adata.obs.cell_type_multiplet.unique() if 'beta' in ct]

# %% [markdown]
# #C: No beta str containing cell types to exclude

# %%
# Subset adata
selected_beta=[ct for ct in adata.obs.cell_type_multiplet.unique() if 'beta' in ct]
adata_beta=adata[adata.obs.cell_type.isin(selected_beta),:].copy()
adata_beta.shape

# Normalise raw data for plotting and cell type scoring
adata_raw_beta=adata_beta.raw.to_adata().copy()
# Normalize and log transform
adata_raw_beta.X /= adata_raw_beta.obs['size_factors'].values[:,None] # This reshapes the size-factors array
sc.pp.log1p(adata_raw_beta)
adata_raw_beta.X = sparse.csr_matrix(np.asarray(adata_raw_beta.X))

# Scale beta adata for umap
adata_scl_beta=adata_beta
del adata_beta
sc.pp.scale(adata_scl_beta,max_value=10)
sc.pp.pca(adata_scl_beta, n_comps=10, use_highly_variable=True, svd_solver='arpack')
sc.pp.neighbors(adata_scl_beta,n_pcs=10)
sc.tl.umap(adata_scl_beta)

# Combine raw and X data
adata_rawnormalised_beta=adata_scl_beta.copy()
adata_rawnormalised_beta.raw=adata_raw_beta
del adata_raw_beta

# %%
metadata=pd.read_excel('/lustre/groups/ml01/workspace/karin.hrovatin/data/pancreas/scRNA/scRNA-seq_pancreas_metadata.xlsx',
                      sheet_name='Fltp_2y')
# Add metadata 
samples=adata_rawnormalised_beta.obs.file.unique()
value_map={sample:metadata.query('sample_name =="'+sample+'"')['design'].values[0] for sample in samples}
adata_rawnormalised_beta.obs['design']=adata_rawnormalised_beta.obs.file.map(value_map)

# %%
rcParams['figure.figsize']=(4,4)
random_indices=np.random.permutation(list(range(adata_rawnormalised_beta.shape[0])))
sc.pl.umap(adata_rawnormalised_beta[random_indices,:], color=['design','file'],size=10, use_raw=True,wspace=0.3)

# %% [markdown]
# #### Check markers

# %%
# Select beta and endocrine markers and group by cell type and subtype
for group_name, group in markers.query('Cell in ["beta","endocrine"]').fillna('/').groupby(['Cell','Subtype']):
    print(group_name)
    genes=group.Gene
    # Retain genes present in raw var_names
    missing=[gene for gene in genes if gene not in adata.raw.var_names]
    genes=[gene for gene in genes if gene in adata.raw.var_names]
    print('Missing genes:',missing)
    rcParams['figure.figsize']=(4,4)
    sc.pl.umap(adata_rawnormalised_beta, color=['cell_type'],size=10, use_raw=True)
    sc.pl.umap(adata_rawnormalised_beta, color=genes ,size=10, use_raw=True)

# %% [markdown]
# #C: Small ins low population. Aging markers are all ower UMAP so will not be annotated specifically. Etv5 is similar but less distinct than Etv1 - only Etv1 will be annotated as this cell type was recognised elsewhere and seems to represent similar populations. Slc2a2 will note be included in mature as Mafa and Ucn3 have more distinct expression patters. Chgb seems to separate beta cells in two large subpopulations, both of which have subpopulations of other markers. However, as Chgb is not separated by batches (unlike Ccl5) it will be annotated with other cell markers and not separately.

# %%
# Selected markers that seem to be able to distinguish between cell seubtypes
markers_selection_beta={
'Etv1_high':['Etv1'],
'Cd81_high':['Cd81'],
'Cxcl10_high':['Cxcl10'],
'mature':['Mafa','Ucn3'],
'immature':['Rbp4','Pyy'],
'Chgb_high':['Chgb'],
'ins_high':['Ins1','Ins2']
}

# %% [markdown]
# #### Calculate subpopulation scores

# %%
# Calculate scores
scores=[]
for cell_type,genes in markers_selection_beta.items():
    score_name=cell_type+'_score'
    scores.append(cell_type+'_score')
    sc.tl.score_genes(adata_rawnormalised_beta, gene_list=genes, score_name=score_name,  use_raw=True)

# %%
# Scores normalised to interval [0,1] for each cell type - so that they can be more easily compared
scores_df_norm_beta=adata_rawnormalised_beta.obs[scores]
scores_df_norm_beta=pd.DataFrame(pp.minmax_scale(scores_df_norm_beta),columns=scores_df_norm_beta.columns,index=adata_rawnormalised_beta.obs.index)

# %% [markdown]
# #### Score distn and relationships

# %%
# Plot of normalised scores distribution in whole dataset, per cluster
rcParams['figure.figsize']=(20,3)
fig,ax=plt.subplots()
sb.violinplot(data=scores_df_norm_beta,inner=None,ax=ax)
ax.grid()

# %%
# Convert ins high to ins low
scores_df_norm_beta['ins_low_score']=scores_df_norm_beta['ins_high_score']*-1+1

# %%
# Dict for score thresholds
beta_marker_thresholds=dict()

# %%
# Find immature
rcParams['figure.figsize']=(4,4)
plt.scatter(scores_df_norm_beta['immature_score'],scores_df_norm_beta['mature_score'],s=0.1)
plt.xlabel('immature_score')
plt.ylabel('mature_score')

# %% [markdown]
# Dist of differences between mature and immature

# %%
scores_df_norm_beta['immature-mature_score']=scores_df_norm_beta['immature_score']-scores_df_norm_beta['mature_score']

# %%
a=plt.hist(scores_df_norm_beta['immature-mature_score'],bins=70)
beta_marker_thresholds['immature-mature_score']=0
plt.axvline(beta_marker_thresholds['immature-mature_score'],c='r')
plt.xlabel('immature-mature score')

# %%
plt.scatter(scores_df_norm_beta['immature_score'],scores_df_norm_beta['mature_score'],s=0.2,
            c=scores_df_norm_beta['immature-mature_score']>=beta_marker_thresholds['immature-mature_score'],
            cmap='PiYG')
plt.xlabel('immature_score')
plt.ylabel('mature_score')

# %%
plt.scatter(scores_df_norm_beta['Cd81_high_score'],scores_df_norm_beta['immature-mature_score'],s=0.1)
plt.xlabel('Cd81_high_score')
plt.ylabel('immature-mature_score')

# %%
a=plt.hist(scores_df_norm_beta['Cd81_high_score'],bins=70)
#plt.yscale('log')
plt.ylabel('Cd81_high_score')
beta_marker_thresholds['Cd81_high_score']=0.46
plt.axvline(beta_marker_thresholds['Cd81_high_score'],c='r')

# %%
a=plt.hist(scores_df_norm_beta['ins_low_score'],bins=70)
plt.yscale('log')
plt.ylabel('ins_low_score')
beta_marker_thresholds['ins_low_score']=0.59
plt.axvline(beta_marker_thresholds['ins_low_score'],c='r')

# %%
a=plt.hist(scores_df_norm_beta['Etv1_high_score'],bins=50)
#plt.yscale('log')
plt.ylabel('Etv1_high_score')
beta_marker_thresholds['Etv1_high_score']=0.4
plt.axvline(beta_marker_thresholds['Etv1_high_score'],c='r')

# %%
plt.scatter(scores_df_norm_beta['Cd81_high_score'],scores_df_norm_beta['Etv1_high_score'],s=0.1)
plt.xlabel('Cd81_high_score')
plt.ylabel('Etv1_high_score')

# %%
plt.scatter(scores_df_norm_beta['immature-mature_score'],scores_df_norm_beta['Etv1_high_score'],s=0.1)
plt.xlabel('immature-mature_score')
plt.ylabel('Etv1_high_score')

# %%
a=plt.hist(scores_df_norm_beta['Cxcl10_high_score'],bins=50)
#plt.yscale('log')
plt.ylim((0,1000))
plt.ylabel('Cxcl10_high_score')
beta_marker_thresholds['Cxcl10_high_score']=0.3
plt.axvline(beta_marker_thresholds['Cxcl10_high_score'],c='r')

# %%
a=plt.hist(scores_df_norm_beta['Chgb_high_score'],bins=70)
#plt.yscale('log')
plt.ylabel('Chgb_high_score')
beta_marker_thresholds['Chgb_high_score']=0.42
plt.axvline(beta_marker_thresholds['Chgb_high_score'],c='r')

# %%
# Thresholds for cell type assignemnt based on normalised scores
scores_cols_beta=['immature-mature_score','Cd81_high_score','Etv1_high_score','ins_low_score','Cxcl10_high_score',
                 'Chgb_high_score']
thresholds_beta=[beta_marker_thresholds[score_col] for score_col in scores_cols_beta]

# %%
# Assign cell types based on scores to each cell
assignment_df_beta=scores_df_norm_beta[scores_cols_beta]>=thresholds_beta
# replace '-mature' from immature-mature to get just immature out for the cell type name
assignment_df_beta.columns=[col.replace('_score','').replace('-mature','') for col in scores_cols_beta] 

# %%
# For each cell make a (standard) string of annotated cell types: 
# e.g. each annotated cell type in the same order, separated by '_' when multiple cell types were annotated
type_unions_beta=[]
for idx,row in assignment_df_beta.iterrows():
    type_union=''
    for col in row.index:
        # Remove Ccl5 from union of cell types
        if row[col]:
            type_union=type_union+col+'_'
    if type_union=='':
        type_union='NA'
    type_unions_beta.append(type_union.rstrip('_'))

# %%
# Add cell types strings of cells to scores/assignment DF
assignment_df_beta['type_union']=type_unions_beta
assignment_df_beta['type_union'].value_counts()

# %%
adata_rawnormalised_beta.obs['beta_subtype']=assignment_df_beta['type_union']

# %%
rcParams['figure.figsize']=(4,4)
sc.pl.umap(adata_rawnormalised_beta,color='beta_subtype')

# %% [markdown]
# #C: Adjust threshold so that high patterns observed on UMAps above can be seen here as well.

# %%
for subtype,count in adata_rawnormalised_beta.obs.beta_subtype.value_counts().iteritems():
    if subtype !='NA':
        s=40 if count < 100 else 15
        adata_rawnormalised_beta.obs['temp']=adata_rawnormalised_beta.obs['beta_subtype']==subtype
        sc.pl.umap(adata_rawnormalised_beta,color='temp',size=s,title=subtype)
adata_rawnormalised_beta.obs.drop('temp',axis=1,inplace=True)

# %% [markdown]
# #C: Set less common cell types to more common ones based on UMAP position. If none of the individual cell types is common or the population is based on single cell type with low count set it to NA which will be interpreted as beta.

# %%
# rename cell types
adata_rawnormalised_beta.obs['beta_subtype'].replace({
 'immature_Cd81_high_Chgb_high':'immature_Chgb_high',
 'immature_Etv1_high_Chgb_high':'Etv1_high_Chgb_high',
 'Etv1_high_Cxcl10_high_Chgb_high':'Etv1_high_Chgb_high',
 'immature_Cd81_high_Etv1_high_Chgb_high':'Cd81_high_Etv1_high_Chgb_high',
 'immature_Cd81_high_Cxcl10_high_Chgb_high':'immature_Cxcl10_high_Chgb_high',
 'immature_Cd81_high':'immature',
 'Cd81_high_Cxcl10_high':'Cd81_high',
 'Etv1_high_Cxcl10_high':'Etv1_high',
 'immature_Cd81_high_Etv1_high':'Cd81_high_Etv1_high',
 'immature_Etv1_high_Cxcl10_high_Chgb_high':'Etv1_high_Chgb_high',
 'Cd81_high_Etv1_high_Cxcl10_high':'Cd81_high_Etv1_high',
 'immature_Cd81_high_ins_low_Chgb_high':'immature_Chgb_high',
 'Etv1_high_ins_low':'Etv1_high',
 'Cd81_high_Etv1_high_Cxcl10_high_Chgb_high':'Cd81_high_Etv1_high_Chgb_high',
 'immature_Cxcl10_high':'immature',
 'Cd81_high_ins_low_Chgb_high':'Cd81_high_Chgb_high',
 'Etv1_high_ins_low_Chgb_high':'Etv1_high_Chgb_high',
 'ins_low_Chgb_high':'Chgb_high',
 'ins_low':'NA',
 'immature_Cd81_high_ins_low':'immature',
 'immature_Cd81_high_Etv1_high_Cxcl10_high_Chgb_high':'immature_Cxcl10_high_Chgb_high',
 'Cd81_high_Etv1_high_ins_low_Chgb_high':'Cd81_high_Etv1_high_Chgb_high',
 'Cd81_high_Etv1_high_ins_low':'Cd81_high_Etv1_high',
 'immature_Etv1_high_ins_low_Chgb_high':'Etv1_high_Chgb_high',
 'immature_ins_low':'NA',
 'immature_Cd81_high_Cxcl10_high':'NA',
 'Cd81_high_ins_low_Cxcl10_high':'NA',
 'immature_Cd81_high_Etv1_high_Cxcl10_high':'immature',
 'Cd81_high_ins_low':'Cd81_high',
 'immature_Cd81_high_ins_low_Cxcl10_high':'immature',
 'immature_ins_low_Cxcl10_high_Chgb_high':'immature_Cxcl10_high_Chgb_high',
 'immature_Cd81_high_Etv1_high_ins_low_Chgb_high':'immature_Chgb_high',
 'immature_Etv1_high':'Etv1_high'
}, inplace=True)

# %%
adata_rawnormalised_beta.obs.beta_subtype.value_counts()

# %%
for subtype,count in adata_rawnormalised_beta.obs.beta_subtype.value_counts().iteritems():
    if subtype !='NA':
        s=40 if count < 100 else 15
        adata_rawnormalised_beta.obs['temp']=adata_rawnormalised_beta.obs['beta_subtype']==subtype
        sc.pl.umap(adata_rawnormalised_beta,color='temp',size=s,title=subtype)
adata_rawnormalised_beta.obs.drop('temp',axis=1,inplace=True)

# %%
# Add cell type data to adata
adata.obs[['cell_subtype','cell_subtype_multiplet']]=adata.obs[['cell_type','cell_type_multiplet']]
for subtype in adata_rawnormalised_beta.obs['beta_subtype'].unique():
    if subtype != 'NA':
        idxs=adata_rawnormalised_beta.obs.query('beta_subtype == @subtype').index
        subtype='beta_'+subtype
        add_category(df=adata.obs,idxs=idxs,col='cell_subtype',category=subtype)
        add_category(df=adata.obs,idxs=idxs,col='cell_subtype_multiplet',category=subtype)
# reorder categories
adata.obs.cell_subtype=pd.Categorical(adata.obs.cell_subtype,
                                   categories=sorted(list(adata.obs.cell_subtype.unique())),ordered=True)
adata.obs.cell_subtype_multiplet=pd.Categorical(adata.obs.cell_subtype_multiplet,
                                  categories=sorted(list(adata.obs.cell_subtype_multiplet.unique())),ordered=True)

# %%
sc.pl.embedding(adata,'X_umap_scl',color='cell_subtype_multiplet')

# %% [markdown]
# ### Save annotation

# %%
if SAVE:
    h.save_h5ad(adata, shared_folder+"data_annotated.h5ad",unique_id2=UID2)

# %%
#adata=h.open_h5ad(shared_folder+"data_annotated.h5ad",unique_id2=UID2)

# %%

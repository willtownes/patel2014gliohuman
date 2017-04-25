# patel2014gliohuman

This package contains a Bioconductor `Summarized Experiment`
  from the [Patel et al. (2014)](https://doi.org/10.1126/science.1254257) paper that performed single cell RNA-Seq
  analysis on human glioblastoma tissue. There are also some cell line
  and bulk RNA-Seq samples included. Metadata was obtained from Gene
  Expression Omnibus and raw FASTQ files were downloaded from Sequence
  Read Archive. All samples were quantified using Kallisto. The data
  provided are the estimated counts for ENSEMBL genes for all samples,
  not just the ones that were included in the authors' analysis.
  There are two `SummarizedExperiment` objects:
 (1) estimated counts from Kallisto and (2) TPMs from Kallisto. 


# Installation

The R-package **patel2014gliohuman** can be installed from Github using the R
package **devtools**.
```s
library(devtools)
install_github("willtownes/patel2014gliohuman")
```
# Load data

The data is provided as a `SummarizedExperiment` object can be loaded 
by running the following code in R: 

```r
library(SummarizedExperiment)
library(patel2014gliohuman)
data(patel2014gliohuman_counts) # object name: patel_glio_2014
data(patel2014gliohuman_tpm) # object name: patel_glio_2014_tpm

# Get the expression data in the form of counts
patel_counts = as.data.frame(as.matrix(assay(patel_glio_2014)))

# Get the expression data in the form of TPMs
patel_tpm = as.data.frame(as.matrix(assay(patel_glio_2014_tpm)))

# Get the pheno data
pdata = colData(patel_glio_2014)
```

# Bug reports
Report bugs as issues on the [GitHub repository](https://github.com/willtownes/patel2014gliohuman)

# Contributors

* [Will Townes](https://github.com/willtownes)
* [Stephanie Hicks](https://github.com/stephaniehicks)

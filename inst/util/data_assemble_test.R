#This file contains tests for the data_assemble.r functions
#to run the tests, in an R terminal cd to inst/util folder
#then load library(testthat) and test_file("data_assemble_test.R")

library(testthat)
context("verify coo2matrix works")
source("../util/data_assemble.r")

#input data
genes<-c("g","a","a","b","d","c")
cells<-c("c3","c1","c2","c1","c3","c1")
vals<-c(1,2,3,4,5,6)
#expected output data
correct_mat<-matrix(0,nrow=5,ncol=3)
rownames(correct_mat)<-c("a","b","c","d","g")
colnames(correct_mat)<-paste0("c",1:3)
correct_mat[1:3,1]<-c(2,4,6)
correct_mat[1,2]<-3
correct_mat[4:5,3]<-c(5,1)

A<-coo2matrix(genes,cells,vals)

test_that("coo2matrix produces sparseMatrix", expect_is(A,"sparseMatrix"))
test_that("coo2matrix has correct dimnames",{
  expect_equal(colnames(A),sort(unique(cells)))
  expect_equal(rownames(A),sort(unique(genes)))
})
test_that("coo2matrix gives correct values",{
  expect_equal(as.matrix(A),correct_mat)
})


#### Here is some stuff for translating sqldf query into base R
library(sqldf)

d<-data.frame(cell_id=sample.int(10,size=50,replace=TRUE),sample=rep(c("A","B"),each=25),gene_id=sample.int(20,size=50,replace=TRUE),est_counts=rpois(50,5))

d_sql<-sqldf("select cell_id,gene_id,sum(est_counts) as est_counts from d group by cell_id,gene_id")
d_agg<-aggregate(est_counts~gene_id+cell_id,d,sum)


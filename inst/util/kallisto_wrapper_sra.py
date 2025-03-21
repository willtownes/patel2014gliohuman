"""
Modified Kallisto Wrapper for case of single end reads where there are multiple fastq files for each sample and an index file telling which file goes with which sample.
Inputs:
* directory containing FASTQ files
* output directory for kallisto results.
* CSV file path containing mapping of files to samples.

Typical Use:
python ../util/kallisto_wrapper_sra.py data/original/fastq data/original/kallisto_out extdata/SraRunInfo_SRP006834.csv
"""

import kallisto_wrapper as kw
from misc import mkdir_p
from itertools import imap
import shlex,subprocess
from csv import DictReader
from os import path
from numpy import array,median

def arghandler(args=None):
    '''parses a list of arguments (default is sys.argv[1:]), such as those from sys.argv and returns the parameters needed for quantifying fastq files with kallisto.'''
    helpmsg = '''This kallisto wrapper script takes as input a directory with FASTQ files and a CSV file mapping files to sample IDs (such as generated from SRA), runs kallisto quantification on all files in parallel using the BSUB (LSF) system, then outputs the results into the specified output folder.'''
    parser = kw.ArgumentParser(description=helpmsg)
    parser.add_argument("input_folder",type=str,help="Location of the folder containing fastq.gz files")
    parser.add_argument("output_folder",type=str,help="Location of the folder for storing Kallisto output")
    parser.add_argument("runinfo_csv",type=str,help="Location of the csv file containing SRA run information. It should have at least the following column names 'SampleName', 'LibraryLayout', 'ScientificName', 'avgLength', and 'Run'. SampleName is the GEO accession ID that uniquely identifies a sample. Run is the ID for the fastq file. If LibraryLayout is 'SINGLE' the fastq file should be like run_1.fastq.gz. If LibraryLayout is 'PAIRED' there should be two files run_1.fastq.gz and run_2.fastq.gz. ScientificNames currently parsed include 'Mus musculus' and 'Homo sapiens'. These are used to indicate which transcriptome should be used. Finally, 'avgLength' is the average fragment length in the fastq file, which is needed by kallisto")
    parser.add_argument("-t","--transcriptome-folder",type=str,default="../resources",dest="tf",help="Folder where transcriptomes are stored. Defaults to ../resources")
    parser.add_argument('-v','--verbose',type=bool,default=False,dest="verbose",help="flag for printing detailed output")
    args = parser.parse_args(args) #if args is None, this will automatically parse sys.argv[1:]
    return args

def get_fastq_dict(runinfo_csv):
    """build dictionary representation of a CSV file mapping SRA runs to sample IDs. Dictionary has structure:
    {sample1:
        {"fastq_list":[srr123,srr456,...],"is_paired_end":True,"species":"Homo sapiens","avgLengths":[55,83,...]},
        ...
    sample2:....}
    """
    with open(path.normpath(runinfo_csv)) as csvfile:
        reader = DictReader(csvfile)
        fastq_dict={}
        for row in reader:
            s = row["SampleName"]
            r = row["Run"]
            species = row["ScientificName"]
            if row["LibraryLayout"].upper() == "SINGLE":
                is_paired_end = False
                #fastq_dict[s]["is_paired_end"] = False
            elif row["LibraryLayout"].upper() == "PAIRED":
                is_paired_end = True
                #fastq_dict[s]["is_paired_end"] = True
            else:
                raise kw.Kallisto_Wrapper_Error("Invalid Paired End Designation for Run %s"%r)
            if species not in kw.SPECIES:
                raise kw.Kallisto_Wrapper_Error("Invalid Species %s in run %s, expecting one of %s"%(species,r,kw.SPECIES))

            try: #case where multiple runs per sample
                fastq_dict[s]["fastq_list"].append(r)
                fastq_dict[s]["avgLengths"].append(int(row["avgLength"]))
                if fastq_dict[s]["is_paired_end"] != is_paired_end:
                    raise kw.Kallisto_Wrapper_Error("Paired end designation inconsistent for sample %s"%s)
                if fastq_dict[s]["species"] != species:
                    raise kw.Kallisto_Wrapper_Error("Species designation inconsistent for sample %s"%s)
            except KeyError: #case where this sample not previously encountered
                fastq_dict[s] = {"fastq_list":[r],"is_paired_end":is_paired_end,"species":species,"avgLengths":[int(row["avgLength"])]}
    return fastq_dict

def compute_ideal_kmer(fqdict):
    """given a fastq dictionary as generated by get_fastq_dict function, find the appropriate kmer length such that when the kallisto index is built, there will not be a conflict with the read lengths. Returns a dictionary. The keys are species names. The values are the recommended kmer_size parameter for each species's transcriptome. If the kmer_size is 31, the kmer_size parameter can be omitted from kallisto/salmon command.

    This function matters only for libraries with short reads, especially if the read lengths are less than 31 since it can cause a situation where no reads map.
    https://groups.google.com/forum/#!searchin/kallisto-sleuth-users/0$20reads$20pseudoaligned%7Csort:relevance/kallisto-sleuth-users/Uv9badM-cTE/o5rtsUDLAwAJ

    The formula is, for each sample, find the average fragment length from the SRA metadata. If the sample is paired end, divide this number by two. Then, find the minimum of these numbers across all samples. Take this number and divide by two, rounding down to the nearest odd number. If the result is greater than 31, the result is set to 31 (default encouraged by both kallisto and salmon)."""
    res = {}
    for i in fqdict:
        species = fqdict[i]["species"]
        try: val = res[species]
        except KeyError: val = float("inf") #init new species in result
        minlen = min(fqdict[i]["avgLengths"])
        if fqdict[i]["is_paired_end"]: minlen = minlen/2 #integer division
        res[species] = min(val,minlen)
    for i in res:
        res[i] = res[i]/2
        if res[i] % 2 == 0: res[i] -= 1 #force odd number
        if res[i]>=31: res[i] = None
    return res

def quant(input_folder,fastq_dict,species_kmers,output_folder,transcriptome_folder,bsub_out="bsub_out"):
    """submit jobs to bsub to run kallisto quantification on each pair of fastq files in the fastq dictionary provided, where the files are located in the input_folder."""
    print("Starting new quantification run for batch of %d samples from %s"%(len(fastq_dict),input_folder))
    mkdir_p(bsub_out)
    #no subfolders needed for SRA data
    print("bsub logs stored in %s folder"%bsub_out)
    mkdir_p(output_folder)
    print("kallisto output in %s"%output_folder)
    for i in fastq_dict:
        print("===processing fastq files from sample ID: %s==="%i)
        outdir = path.join(output_folder,i) #separate folder for each fastq, within the output folder
        mkdir_p(outdir)
        cmd = kw.CMD_BASE.format(fastq_id=i,bsub_out=bsub_out)
        cmd = shlex.split(cmd) #convert to list of arguments
        species = fastq_dict[i]["species"]
        t_index = path.join(transcriptome_folder,kw.species2transcriptomeindex(species,kmer_size=species_kmers[species]))
        f1 = [path.join(input_folder,r+"_1.fastq.gz") for r in fastq_dict[i]["fastq_list"]]
        if fastq_dict[i]["is_paired_end"]:
            f2 = [path.join(input_folder,r+"_2.fastq.gz") for r in fastq_dict[i]["fastq_list"]]
            flist = " ".join(imap(lambda x,y: x+" "+y,f1,f2))
            cmd.append("kallisto quant -i {ti} -o {out} {flist}".format(ti=t_index,out=outdir,flist = flist))
        else: #case of single end reads
            flen = median(array(fastq_dict[i]["avgLengths"]))
            flist = " ".join(f1)
            cmd.append("kallisto quant --single -i {ti} -o {out} -l {flen} -s {fsd} {flist}".format(ti=t_index,out=outdir,flen=flen,fsd=flen/5.0,flist = flist))
            #note, fsd is the standard deviation of the fragment length distribution. flen/5 is just a placeholder. We should actually estimate this in the future!
        #print(cmd)
        subprocess.call(cmd)

if __name__=="__main__":
    args = arghandler()
    fastq_dict = get_fastq_dict(args.runinfo_csv)
    species_kmers = compute_ideal_kmer(fastq_dict)
    #unique_species = set([fastq_dict[i]["species"] for i in fastq_dict])
    for s in species_kmers:
        #download any needed transcriptome files
        kw.check_transcriptome(args.tf,s,kmer_size=species_kmers[s])
    quant(args.input_folder,fastq_dict,species_kmers,args.output_folder,args.tf)

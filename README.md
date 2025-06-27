# Overview
This is one of three repositories developed for my [master's thesis](https://lup.lub.lu.se/student-papers/search/publication/9204484) in software engineering, where we explored the impact of Java refactoring on execution performance.

See also the [refactoring framework](https://github.com/kaohl/alfine-refactoring) and the [build framework](https://github.com/kaohl/daivy).

> [!NOTE]
> Regarding citation: Please reference the thesis, which provides context for this work, and links to all repositories.

> [!NOTE]
> Please fork the repository for future work.

# Java Performance Evaluation Framework
The evaluation framework utilizes the refactoring framework and the build framework, linked above, to provide the infrastructure required to study the impact of Java refactoring on execution performance.

The benchmarks and refactoring types available for experimentation can be found in the build and refactoring frameworks, respectively.

# Create an experiment, refactor, and benchmark refactorings
## Prerequisites
- Install Python 3.13.1. Probably works with higher versions. Not sure about lower versions. You may have to install a few python packages to be able to run all scripts in the repository.
- Install SDKMAN!.
- Install one or more Java SDKs of your choice. Please note that some of the available distributions requires a license to use.
- Clone the refactoring framework and export the application into the *refactoring-framework* directory at the root of this repository, using the plugin export wizard from within [Eclipse IDE](https://www.eclipse.org/downloads/packages/release/2024-12/r).
- Clone the build framework into a directory of your choice and set the DAIVY_HOME environment variable to the absolute path of the top-level directory of the cloned repository. It is recommended to add this variable to the *.bashrc* file in your home directory for a smoother user experience.

## Procedure
Please understand that you will need to read the scripts to get a better understanding of how the implementation works. When everything is set up, refactoring and benchmarking can be batched and run automatically. However, manual intervention is required to configure experiments and analyse results. You will need to learn the input/output relation of all the main scripts mentioned below to successfully execute an experiment.

To execute an experiment we perform the following steps:
1. Create an *experiments* directory, for example, by running *generate_experiment.py* after adapting it to your experiment:
```
./generate_experiment.py
```
> [!CAUTION]
> If additional parameters are added after after an experiment is started, the parameter files in all existing data will be incomplete and data processing may fail because of missing values.
>
> It is possible to upgrade an existing dataset, but only if you know the values that should be applied to these parameters for each existing benchmark execution.
>
> Take care to add all parameters from the start.

> [!TIP]
> In contrast, adding additional values for existing parameters can be done at any time to extend the dataset and the analysis.
2. Compute baseline performance:
```
./compute_baseline.py
```
3. Create workspaces for refactoring by running:
```
./evaluation.py --create [--bs <bm> [ <bm>]*] [--ws <wl> [ <wl>]*]
```
4. Generate refactoring patches for one or more workloads:
```
./evaluation.py --refactor [--bs <bm> [ <bm>]*] [--ws <wl> [ <wl>]*] --n <number of iterations>
```
5. Run benchmarks
```
./evaluation.py --benchmark --n <number of iterations>
```
6. Compute ANOVA tables and speedup plots:
```
./plots.py 
```

Note that the *--data* command-line parameter is optional and defaults to *"experiments"*. If you set up multiple experiment directories, you need to set the *--data* parameter accordingly to perform operations on the correct directory.

> [!TIP]
> When running refactoring and benchmarks it is safe to terminate the program at any time. This usually results in one incomplete datapoint on disk. This will cause the analysis script to fail when processing this datapoint. Simply delete the corresponding directory when that happens.

Please refer to the *evaluation.py* script for additional command-line parameters.

## Scripts

There are a number of scripts available at the top-level and within the *scripts* directory that perform tasks that I found useful during experimentation. Please refer to these scripts for more details.

For example, you can use the following to explore the refactoring descriptor cache to some degree. Currently, only *meta* attribute filtering is supported. However, it is easy to extend the matching mechanism to support *args* filtering as well, if/when needed.
```
./opportunity_cache.py \
    --cache experiments/jacop/workspaces/jacop/default/workspace/oppcache \
    --filter "{\"id\":\"org.eclipse.jdt.ui.extract.method\"}" | wc -l
```

# Troubleshooting
## Missing data
If you get the following error, make sure that the linked in data directory actually exists (see build framework). In this case, the directory linked symbolically at '<...>/luindex-1.0/dat' had been removed to save space.
```
===== DaCapo unknown luindex starting =====
FATAL ERROR: Failed to find data at <...>/luindex-1.0

Please run DaCapo with --data-set-location <parent-dir-name> to reset the location of the parent directory.
```


<div align="center">

# **Data Refine Subnet** <!-- omit in toc -->
[![Discord Chat](https://img.shields.io/discord/308323056592486420.svg)](https://discord.gg/bittensor)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) 

---

## Refining Dataset powered by Decentralized network <!-- omit in toc -->

[Discord](https://discord.gg/bittensor) • [Network](https://taostats.io/) • [Research](https://bittensor.com/whitepaper)
</div>

---
- [Introduction](#introduction)
- [Main Mechanism](#main-mechanism-of-subnet)
- [Roadmap](roadmap.md)
- [Installation](#installation)
---

## Introduction

**IMPORTANT**: If you are new to Bittensor subnets, read about [Bittensor Network](https://bittensor.com/whitepaper) and feel the power.  



The performance of large language models (LLMs) is significantly influenced by the quality and scale of their pretraining datasets. While the pretraining datasets for cutting-edge open LLMs like LLaMA 3 and Mixtral are not publicly available, and little is known about their creation, a new large-scale dataset, [FineWeb](https://huggingface.co/datasets/HuggingFaceFW/fineweb), has recently emerged. FineWeb consists of 15 trillion tokens (44TB of disk space) derived from 96 snapshots of [CommonCrawl](https://commoncrawl.org/), and has demonstrated superior performance compared to other open pretraining datasets.
Here's the related blog post - [https://huggingface.co/spaces/HuggingFaceFW/blogpost-fineweb-v1](https://huggingface.co/spaces/HuggingFaceFW/blogpost-fineweb-v1)

In our project, we leverage the same algorithm used to create the FineWeb dataset to build our own, even larger, and higher-performing dataset. This dataset will be enhanced and powered by the decentralized Bittensor network.

The Data Refine Subnet implements an optimized dataset creation mechanism, featuring the following neuron types:

	- Miners: Responsible for generating refined datasets from raw crawled data.
	- Validators: Tasked with evaluating the performance of miners and ensuring the quality of the datasets produced.

Both of them are getting rewards via tao according their score and trust in network.
<div align="center">
   <picture>
      <img width="600" alt="diagram" src="./docs/flow.png">
    </picture>
</div>

<p align="center">
   Subnet Diagram
</p>

## Main Mechanism of Subnet

Miners receive tasks from the task server via the task retrieval API. The task server manages and organizes these tasks, primarily splitting the CommonCrawl data and tracking miners’ status. After processing the task, miners upload the refined dataset to their Hugging Face repository and submit the commit, including the Hugging Face URL, to the blockchain.

Validators periodically check miners’ commits every x blocks to retrieve new submissions. They then evaluate the elapsed time and the quality of the resulting dataset. Based on the miner’s performance, the validators assign weights according to the miners’ scores.

```text
-- how to evaluate dataset --

Validators train a small model using the miner’s dataset and assess the dataset quality based on the model’s accuracy.
If the trained model performs well, it indicates that the dataset is of high quality. Conversely, if the model performs poorly, it suggests that the dataset quality is suboptimal.
This method allows for an effective evaluation of the dataset quality.
```

<div align="center">
   <picture>
      <img width="600" alt="diagram" src="./docs/mechanism.png">
    </picture>
</div>

<p align="center">
   Machanism Diagram
</p>


## Installation

- [Miners](./docs/miner.md)
- [Validators](./docs/validator.md)


## License
This repository is licensed under the MIT License.
```text
# The MIT License (MIT)
# Copyright © 2023 Yuma Rao

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
```

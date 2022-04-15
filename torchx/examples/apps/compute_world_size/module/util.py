#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import os
from ipaddress import ip_address, IPv6Address

import torch
import torch.distributed as dist
import torch.nn.functional as F
from omegaconf import DictConfig


def is_ipv6_address(addr: str) -> bool:
    try:
        return type(ip_address(addr)) is IPv6Address
    except Exception:
        return False


def get_init_method(master_addr: str, master_port: int) -> str:
    if is_ipv6_address(master_addr):
        return f"tcp://[{master_addr}]:{master_port}"
    else:
        return f"tcp://{master_addr}:{master_port}"


def compute_world_size(cfg: DictConfig) -> int:

    rank = int(os.getenv("RANK", cfg.main.rank))
    world_size = int(os.getenv("WORLD_SIZE", cfg.main.world_size))
    master_addr = os.getenv("MASTER_ADDR", cfg.main.master_addr)
    master_port = int(os.getenv("MASTER_PORT", cfg.main.master_port))
    backend = cfg.main.backend

    print(f"initializing `{backend}` process group")
    dist.init_process_group(
        backend=backend,
        init_method=get_init_method(master_addr, master_port),
        rank=rank,
        world_size=world_size,
    )
    print("successfully initialized process group")

    rank = dist.get_rank()
    world_size = dist.get_world_size()

    t = F.one_hot(torch.tensor(rank), num_classes=world_size)
    dist.all_reduce(t)
    computed_world_size = int(torch.sum(t).item())
    print(
        f"rank: {rank}, actual world_size: {world_size}, computed world_size: {computed_world_size}"
    )
    return computed_world_size
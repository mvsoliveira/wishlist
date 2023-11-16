SIM ?= questa
GUI ?= 0
TOPLEVEL_LANG ?= vhdl
DESIGN ?= l1calogfex
VCOM_ARGS=-2008
export COCOTB_RESOLVE_X=RANDOM

PWD=$(shell pwd)

export PYTHONPATH := $(PWD)/../../python:$(PYTHONPATH)

VHDL_SOURCES = axi_lite_ipif_v3_0_vh_rfs.vhd

export BACKANNOTATED_YAML := $(PWD)/../../firmware/$(DESIGN)_backannotated.yaml

TOPLEVEL := axi_lite_ipif
MODULE   := rtl_simulation

include $(shell cocotb-config --makefiles)/Makefile.sim

SIM ?= questa
GUI ?= 1
TOPLEVEL_LANG ?= vhdl
DESIGN ?= l1calogfex
VCOM_ARGS=-2008
export COCOTB_RESOLVE_X=RANDOM

PWD=$(shell pwd)

export PYTHONPATH := $(PWD)/../../python:$(PYTHONPATH)
RTL_LIBRARY = axi_lite_ipif_v3_0_4
VHDL_SOURCES = axi_lite_ipif_v3_0_vh_rfs.vhd example_axilite_wrapper.vhd

SIM_ARGS+=-gC_S_AXI_DATA_WIDTH=32

export BACKANNOTATED_YAML := $(PWD)/../../firmware/$(DESIGN)_backannotated.yaml

TOPLEVEL := example_axilite_wrapper
MODULE   := axi_simulation

include $(shell cocotb-config --makefiles)/Makefile.sim

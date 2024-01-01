# wishlist

## Installing

- [ ] Clonning repository
```
git clone https://gitlab.cern.ch/msilvaol/wishlist.git
```
- [ ] Installing conda encironment
```
conda create --name wishlist --file wishlist/requirements.txt -c conda-forge -y
conda activate wishlist
pip install bigtree
pip install cocotbext-axi
```


## Getting started

- [ ] Activating environment
```
conda activate wishlist
```

## Building and uploading to pip

```
python3 -m build  
python3 -m twine upload dist/* 
```
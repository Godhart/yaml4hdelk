def prints(data, prefix="", indent=4, level=0):
    result = ""
    if not isinstance(data, (list, dict, tuple)):
        result + " "*level*indent + prefix + f"{data}\n"
    elif isinstance(data, dict):
        result += " "*level*indent + "{\n"
        for k, v in data.items():
            result += prints(v, f"`{k}`: ", indent, level+1)
        result += " "*level*indent + "}\n"
    else:
        result += " "*level*indent + "[\n"
        for i in range(0, len(data)):
            result += prints(data[i], f"[{i}]: ", indent, level+1)
        result += " "*level*indent + "]\n"
    return result

import supabase.client
import inspect

for name, obj in inspect.getmembers(supabase.client):
    if inspect.isclass(obj):
        print(f"Class: {name} from module: {obj.__module__}")

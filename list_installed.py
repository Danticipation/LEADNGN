import pkg_resources

# List all installed packages
installed_packages = [d.project_name for d in pkg_resources.working_set]

# Print packages with "mirror" in the name (case insensitive)
print("Packages with 'mirror' in their name:")
for pkg in installed_packages:
    if 'mirror' in pkg.lower():
        print(f"- {pkg}")

print("\nAll installed packages:")
for pkg in sorted(installed_packages):
    print(f"- {pkg}")
#!/bin/bash

# Script to add Swift files to Xcode project
# This uses xcodeproj Ruby gem to modify the project file

echo "Adding Swift files to Xcode project..."

# Check if xcodeproj gem is installed
if ! gem list xcodeproj -i > /dev/null 2>&1; then
    echo "Installing xcodeproj gem..."
    sudo gem install xcodeproj
fi

# Create Ruby script to add files
cat > /tmp/add_files.rb << 'RUBY'
require 'xcodeproj'

project_path = 'iphone_rbg_depth.xcodeproj'
project = Xcodeproj::Project.open(project_path)

# Get the main target
target = project.targets.first
main_group = project.main_group['iphone_rbg_depth']

# Files to add
files_to_add = [
  'iphone_rbg_depth/ARViewController.swift',
  'iphone_rbg_depth/ARViewControllerRepresentable.swift'
]

files_to_add.each do |file_path|
  # Check if file already exists in project
  existing = main_group.files.find { |f| f.path == File.basename(file_path) }

  if existing.nil?
    # Add file reference
    file_ref = main_group.new_reference(file_path)

    # Add to build phase (compile sources)
    target.source_build_phase.add_file_reference(file_ref)

    puts "Added: #{file_path}"
  else
    puts "Already exists: #{file_path}"
  end
end

# Save the project
project.save

puts "Done!"
RUBY

# Run the Ruby script
ruby /tmp/add_files.rb

# Clean up
rm /tmp/add_files.rb

echo "Files added successfully! You can now build the project in Xcode."

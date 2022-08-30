#![allow(dead_code)]

#[macro_use]
extern crate hello_world_macro_derive;

trait HelloWorld {
    fn hello_world(); 
}

#[derive(Debug, HelloWorld)]
struct OhMyStruct {
    name: String,
    age: u8,
}

impl OhMyStruct {
    pub fn new<S: Into<String>>(name: S) -> Self {
        return OhMyStruct {
            name: name.into(),
            age: 42,
        }
    }
}

impl OhMyStruct {
    pub fn hello_space(self: &Self) {
        println!("Hello space!")
    }
}

#[macro_export]
macro_rules! new_oh_my_struct {
    ($name:expr) => (OhMyStruct::new($name))
}

fn main() {
    let oh_my_struct = new_oh_my_struct!("Frodo");
    println!("Structured macro creation: {:?}", oh_my_struct);
    oh_my_struct.hello_space();

    OhMyStruct::hello_world();

    println!("Derived macro struct: {:?}", OhMyGosh{name: "First".to_string(), age: "One".to_string()});
}

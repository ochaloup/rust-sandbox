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

#[macro_export]
macro_rules! new_oh_my_struct {
    ($name:expr) => (OhMyStruct::new($name))
}

fn main() {
    // println!("Hello, world! {:?}", new_oh_my_struct!("Frodo"));
    OhMyStruct::hello_world();
}
